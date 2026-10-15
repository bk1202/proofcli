"""Bounded process I/O and ownership of ordinary descendants; no reader threads."""

from dataclasses import dataclass, field
import base64
import os
import signal
import subprocess
import time

CAPTURE_LIMIT = 1024 * 1024


class RunInterrupted(KeyboardInterrupt):
    def __init__(self, signum=signal.SIGINT):
        self.signum = signum


@dataclass
class Result:
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    interrupted_signal: int | None = None
    truncated: dict = field(default_factory=lambda: {"stdout": False, "stderr": False})
    incomplete: bool = False
    encoding_errors: dict = field(default_factory=dict)
    bytes_base64: dict = field(default_factory=dict)
    error: str | None = None


def _read(pipe):
    if os.name == "nt":
        from .winjob import pipe_available
        available = pipe_available(pipe.fileno())
        if available is None:
            return b""
        if available == 0:
            return None
        return os.read(pipe.fileno(), min(65536, available))
    try:
        return os.read(pipe.fileno(), 65536)
    except BlockingIOError:
        return None


def _terminate(process, job):
    try:
        if job is not None:
            job.terminate()
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)


def run_process(argv, cwd, timeout, *, env=None):
    """Defer owned interrupt handlers until a complete pipe read is retained.

    Raising from a signal handler can discard bytes already consumed by os.read
    before Python stores its return value. Latching requests also keeps spawn
    and bounded cleanup from being interrupted between ownership operations.
    """
    pending = [None]
    handlers = {}
    def requested(signum, frame):
        if pending[0] is None:
            pending[0] = signum
    try:
        for signum in dict.fromkeys((signal.SIGINT, signal.SIGTERM, getattr(signal, "SIGBREAK", signal.SIGINT))):
            original = signal.getsignal(signum)
            if original is signal.default_int_handler or getattr(original, "_proofcli_interrupt", False):
                try:
                    signal.signal(signum, requested)
                except ValueError:  # Embedded invocation outside the main thread.
                    break
                handlers[signum] = original
        result = _run_process(argv, cwd, timeout, env=env, pending=pending)
    finally:
        for signum, handler in handlers.items():
            signal.signal(signum, handler)
    if pending[0] is not None:
        result.interrupted_signal = pending[0]
    return result


def _run_process(argv, cwd, timeout, *, env, pending):
    """Retain at most CAPTURE_LIMIT bytes per stream and stop on first overflow.

    Pipes are read only when ready. A detached process retaining a pipe cannot
    keep the caller blocked: final draining has a separate bounded deadline.
    """
    result = Result()
    job = None
    process = None
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    pipes = {}
    started = time.monotonic()
    cleaned = False
    def collect_available():
        progressed = False
        for name, pipe in list(pipes.items()):
            data = _read(pipe)
            if data is None:
                continue
            progressed = True
            if not data:
                pipe.close()
                del pipes[name]
                continue
            room = CAPTURE_LIMIT - len(buffers[name])
            buffers[name].extend(data[:room])
            if len(data) > room:
                result.truncated[name] = True
        return progressed

    def drain():
        deadline = time.monotonic() + 0.5
        while pipes and time.monotonic() < deadline:
            if not collect_available():
                time.sleep(0.005)
        result.incomplete = bool(pipes)

    try:
        if os.name == "nt":
            from .winjob import WindowsJob
            job = WindowsJob()
        process = subprocess.Popen(
            argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0,
            shell=False, start_new_session=(os.name != "nt"),
            creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP | 0x4) if job else 0,
        )
        pipes = {"stdout": process.stdout, "stderr": process.stderr}
        if job:
            job.assign(int(process._handle))
            job.resume(process.pid)
        else:
            for pipe in pipes.values():
                os.set_blocking(pipe.fileno(), False)
        draining_until = None
        while True:
            progressed = collect_available()
            if pending[0] is not None:
                result.interrupted_signal = pending[0]
                break
            now = time.monotonic()
            if not cleaned:
                result.timed_out = process.poll() is None and now - started >= timeout
                if process.poll() is not None or result.timed_out or any(result.truncated.values()):
                    _terminate(process, job)
                    cleaned = True
                    draining_until = time.monotonic() + 0.5
            if cleaned and not pipes:
                break
            if cleaned and time.monotonic() >= draining_until:
                result.incomplete = bool(pipes)
                break
            if not progressed:
                time.sleep(0.005)
    except KeyboardInterrupt as exc:
        result.interrupted_signal = getattr(exc, "signum", signal.SIGINT)
    except OSError as exc:
        if process is None:
            raise
        result.error = f"process supervision failed: {exc}"
    finally:
        if process is not None:
            try:
                if not cleaned:
                    _terminate(process, job)
                if not cleaned or pending[0] is not None:
                    # Retain queued bytes even if interruption arrived during
                    # final draining after ordinary process-tree cleanup.
                    drain()
                result.returncode = process.returncode
            except (OSError, subprocess.TimeoutExpired) as exc:
                result.error = f"process cleanup failed: {exc}"
                result.incomplete = bool(pipes)
            finally:
                for pipe in (process.stdout, process.stderr):
                    if pipe is not None:
                        pipe.close()
        if job:
            try:
                job.close()
            except OSError as exc:
                result.error = f"job cleanup failed: {exc}"
    for name, buffer in buffers.items():
        data = bytes(buffer)
        try:
            text = data.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            result.encoding_errors[name] = {"start": exc.start, "end": exc.end, "reason": exc.reason}
            result.bytes_base64[name] = base64.b64encode(data).decode("ascii")
            text = data.decode("utf-8", errors="replace")
        setattr(result, name, text)
    return result
