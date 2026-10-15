"""Run one synchronous process in a fresh directory and inspect its results."""

import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

from .spec import SpecError, validate_spec
from .assertions import validate_file_content

CAPTURE_LIMIT = 1024 * 1024


def _check(name, passed, expected, actual):
    return {"name": name, "passed": passed, "expected": expected, "actual": actual}


def error_report(message):
    return {
        "schema_version": 1, "status": "error", "name": "command", "argv": [],
        "exit_code": None, "timed_out": False, "duration_seconds": 0,
        "workdir": None, "stdout": "", "stderr": "", "checks": [], "error": str(message),
    }


def _executable(argv):
    argv = list(argv)
    if argv[0] == "{python}":
        argv[0] = sys.executable
    program = argv[0]
    if os.name == "nt" and Path(program).suffix.lower() in (".cmd", ".bat"):
        raise SpecError("Windows .cmd/.bat executables require a shell; invoke an explicit interpreter instead")
    if not Path(program).is_absolute() and ("/" in program or "\\" in program):
        raise SpecError("executable must be an absolute path or a name on PATH")
    resolved = shutil.which(program)
    if resolved:
        resolved = str(Path(resolved).resolve())
        if os.name == "nt" and Path(resolved).suffix.lower() in (".cmd", ".bat"):
            raise SpecError("Windows .cmd/.bat executables require a shell; invoke an explicit interpreter instead")
        argv[0] = resolved
    else:
        # Do not fall through to the OS loader's different PATH/PATHEXT rules.
        raise FileNotFoundError(f"executable not found: {program}")
    return argv


def _stop(process, job):
    try:
        if job is not None:
            job.terminate()
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    finally:
        # A job API failure must not strand an unassigned, suspended process.
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)


def _execute(argv, root, out, err, timeout):
    job = None
    if os.name == "nt":
        from .winjob import WindowsJob
        job = WindowsJob()
    try:
        process = subprocess.Popen(
            argv, cwd=root, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
            shell=False, start_new_session=(os.name != "nt"),
            # Assign the suspended process to the job before it can spawn children.
            creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP | 0x00000004) if job else 0,
        )
        try:
            if job:
                job.assign(int(process._handle))
                job.resume(process.pid)
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                _stop(process, job)
                return process.returncode, True
        except BaseException:
            # Also handles assignment/resume failure before any user code executes.
            _stop(process, job)
            raise
        return process.returncode, False
    finally:
        if job:
            job.close()


@contextmanager
def _work_directory():
    directory = tempfile.mkdtemp(prefix="proofcli-")
    try:
        yield directory
    finally:
        def writable_retry(function, path, error):
            os.chmod(path, stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
            function(path)

        # Windows may release descendants' cwd handles slightly after termination.
        # Avoid Python 3.10 TemporaryDirectory's recursive retry on a locked cwd.
        for attempt in range(10):
            try:
                if os.path.exists(directory):
                    shutil.rmtree(directory, onerror=writable_retry)
                break
            except OSError:
                if attempt == 9:
                    raise
                time.sleep(0.1)


def _capture(handle):
    handle.seek(0)
    data = handle.read(CAPTURE_LIMIT + 1)
    return data[:CAPTURE_LIMIT].decode("utf-8", errors="replace"), len(data) > CAPTURE_LIMIT


def _file_check(root, expected):
    name = expected["path"]
    minimum = expected.get("min_size", 0)
    target = root.joinpath(*name.split("/"))
    actual = {"exists": False, "size": None}
    try:
        # Resolve symlinks/junctions before accepting any output, including parent dirs.
        resolved = target.resolve()
        if not resolved.is_relative_to(root):
            actual["error"] = "path resolves outside the work directory"
            return _check(f"file:{name}", False, {"regular_file": True, "min_size": minimum}, actual)
        info = resolved.stat()
        actual.update(exists=True, size=info.st_size, regular_file=stat.S_ISREG(info.st_mode))
        passed = actual["regular_file"] and info.st_size >= minimum
    except (OSError, RuntimeError) as exc:
        actual["error"] = str(exc)
        passed = False
    return _check(f"file:{name}", passed, {"regular_file": True, "min_size": minimum}, actual)


def _resolve_inputs(spec, spec_dir):
    sources = []
    for item in spec.get("inputs", []):
        source = spec_dir.joinpath(*item["source"].split("/")).resolve()
        if not source.is_relative_to(spec_dir) or not source.is_file():
            raise SpecError(f"input must be a regular file inside the spec directory: {item['source']}")
        sources.append((source, item["dest"]))
    return sources


def _save_artifacts(root, expected_files, destination):
    saved = []
    for expected in expected_files:
        source = root.joinpath(*expected["path"].split("/")).resolve()
        if not source.is_relative_to(root) or not source.is_file():
            continue
        target = destination.joinpath(*expected["path"].split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        saved.append({"path": expected["path"], "saved_to": str(target), "size": target.stat().st_size})
    return saved


def run_spec(spec, *, spec_dir=None, artifacts_dir=None):
    """Return a JSON-serializable report. Invalid contracts raise SpecError."""
    spec = validate_spec(spec)
    spec_dir = Path(spec_dir if spec_dir is not None else Path.cwd()).resolve()
    if not spec_dir.is_dir():
        raise SpecError(f"spec directory does not exist: {spec_dir}")
    sources = _resolve_inputs(spec, spec_dir)
    destination = None
    if artifacts_dir is not None:
        destination = Path(artifacts_dir).resolve()
        # Refuse overwrite before executing any command. Each run gets new evidence.
        if destination.exists():
            raise SpecError(f"artifact directory already exists; choose a new path: {destination}")
        destination.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    report = {
        "schema_version": 1, "status": "failed", "name": spec["name"], "argv": list(spec["argv"]),
        "exit_code": None, "timed_out": False, "duration_seconds": 0,
        "workdir": None, "stdout": "", "stderr": "", "checks": [],
        "artifacts_dir": str(destination) if destination else None, "artifacts": [],
    }
    checks = report["checks"]
    # Capture outside the workdir so child output cannot collide with expected files.
    # Files rather than pipes avoid deadlock when descendants inherit output handles.
    with _work_directory() as directory:
        root = Path(directory).resolve()
        report["workdir"] = str(root)
        for source, relative in sources:
            target = root.joinpath(*relative.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        argv = [arg.replace("{spec_dir}", str(spec_dir)).replace("{work_dir}", str(root))
                for arg in spec["argv"]]
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            try:
                argv = _executable(argv)
                report["argv"] = argv
                report["exit_code"], report["timed_out"] = _execute(
                    argv, root, out, err, spec["timeout_seconds"],
                )
            except OSError as exc:
                report["error"] = f"cannot start command: {exc}"
                checks.append(_check("spawn", False, "command starts", str(exc)))
            report["stdout"], out_truncated = _capture(out)
            report["stderr"], err_truncated = _capture(err)
        report["output_truncated"] = {"stdout": out_truncated, "stderr": err_truncated}
        checks.append(_check("timeout", not report["timed_out"], spec["timeout_seconds"], report["timed_out"]))
        checks.append(_check("exit_code", report["exit_code"] == spec["expect"]["exit_code"],
                             spec["expect"]["exit_code"], report["exit_code"]))
        checks.append(_check("output_capture", not (out_truncated or err_truncated),
                             f"at most {CAPTURE_LIMIT} bytes per stream", report["output_truncated"]))
        for stream in ("stdout", "stderr"):
            key = f"{stream}_regex"
            if key in spec["expect"]:
                pattern = spec["expect"][key]
                matched = re.search(pattern, report[stream]) is not None
                checks.append(_check(key, matched, pattern, {"matched": matched}))
        for expected in spec["expect"]["files"]:
            file_check = _file_check(root, expected)
            checks.append(file_check)
            if file_check["passed"]:
                checks.extend(validate_file_content(root.joinpath(*expected["path"].split("/")), expected))
        if destination is not None:
            report["artifacts"] = _save_artifacts(root, spec["expect"]["files"], destination)
    report["duration_seconds"] = round(time.monotonic() - started, 6)
    report["status"] = "passed" if all(check["passed"] for check in checks) else "failed"
    return report
