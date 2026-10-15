"""Bounded process I/O and ownership of ordinary descendants; no reader threads."""

from dataclasses import dataclass, field
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
                result.returncode = process.returncode
            except (OSError, subprocess.TimeoutExpired) as exc:
                result.error = f"process cleanup failed: {exc}"
            finally:
                for pipe in (process.stdout, process.stderr):
                    if pipe is not None:
                        pipe.close()
        if job:
            try:
                job.close()
            except OSError as exc:
                result.error = f"job cleanup failed: {exc}"
    result.stdout = bytes(buffers["stdout"]).decode("utf-8", errors="replace")
    result.stderr = bytes(buffers["stderr"]).decode("utf-8", errors="replace")
    return result
