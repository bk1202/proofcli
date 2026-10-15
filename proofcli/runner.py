"""Run one synchronous process in a fresh directory and inspect its results."""

import os
import hashlib
import json
import shutil
import stat
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

from .spec import SpecError, validate_spec
from .process import CAPTURE_LIMIT, run_process


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
        if os.name == "nt" and Path(resolved).resolve().suffix.lower() in (".cmd", ".bat"):
            raise SpecError("Windows .cmd/.bat executables require a shell; invoke an explicit interpreter instead")
        # Dereferencing a venv's Python symlink silently discards that environment.
        argv[0] = os.path.abspath(resolved)
    else:
        # Do not fall through to the OS loader's different PATH/PATHEXT rules.
        raise FileNotFoundError(f"executable not found: {program}")
    return argv


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


def _file_check(root, expected, input_identities=()):
    name = expected["path"]
    minimum = expected.get("min_size", 0)
    target = root.joinpath(*name.split("/"))
    actual = {"exists": False, "size": None}
    try:
        current = root
        for part in name.split("/"):
            current = current / part
            entry = current.lstat()
            if stat.S_ISLNK(entry.st_mode) or getattr(entry, "st_file_attributes", 0) & 0x400:
                raise OSError("output paths must not use symlinks or reparse points")
        # Retain the containment check after rejecting links in every component.
        resolved = target.resolve()
        if not resolved.is_relative_to(root):
            actual["error"] = "path resolves outside the work directory"
            return _check(f"file:{name}", False, {"regular_file": True, "min_size": minimum}, actual)
        info = resolved.stat()
        if [info.st_dev, info.st_ino] in input_identities:
            raise OSError("output aliases a staged input; a distinct output file is required")
        actual.update(exists=True, size=info.st_size, regular_file=stat.S_ISREG(info.st_mode))
        passed = actual["regular_file"] and info.st_size >= minimum
    except (OSError, RuntimeError) as exc:
        actual["error"] = str(exc)
        passed = False
    return _check(f"file:{name}", passed, {"regular_file": True, "min_size": minimum}, actual)


def _resolve_inputs(spec, spec_dir):
    sources = []
    for item in spec.get("inputs", []):
        try:
            source = spec_dir.joinpath(*item["source"].split("/")).resolve()
        except RuntimeError as exc:
            raise SpecError(f"cannot resolve input: {item['source']}: {exc}") from exc
        if not source.is_relative_to(spec_dir) or not source.is_file():
            raise SpecError(f"input must be a regular file inside the spec directory: {item['source']}")
        sources.append((source, item["dest"]))
    return sources


def _save_artifacts(root, expected_files, destination, input_identities):
    saved = []
    for expected in expected_files:
        if not _file_check(root, {"path": expected["path"]}, input_identities)["passed"]:
            continue
        source = root.joinpath(*expected["path"].split("/")).resolve()
        target = destination.joinpath(*expected["path"].split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        saved.append({"path": expected["path"], "saved_to": str(target), "size": target.stat().st_size})
    return saved


def _stage_input(source, target):
    before = source.stat()
    target.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    with source.open("rb") as reader, target.open("xb") as writer:
        while True:
            chunk = reader.read(65536)
            if not chunk:
                break
            writer.write(chunk)
            digest.update(chunk)
    after = source.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns
    ):
        raise SpecError(f"fixture changed while copying: {source}")
    copied = target.stat()
    return {"sha256": digest.hexdigest(), "size": copied.st_size}, [copied.st_dev, copied.st_ino]


def _verify(spec, root, report, identities):
    with tempfile.TemporaryDirectory(prefix="proofcli-verify-") as directory:
        payload = Path(directory) / "input.json"
        output = Path(directory) / "checks.json"
        payload.write_text(json.dumps({"spec": spec, "root": str(root), "stdout": report["stdout"],
                                       "stderr": report["stderr"], "encoding_errors": report.get("output_encoding_errors", {}),
                                       "input_identities": identities}), encoding="utf-8")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path(__file__).resolve().parent.parent) + os.pathsep + env.get("PYTHONPATH", "")
        result = run_process([sys.executable, "-m", "proofcli._verify", str(payload), str(output)],
                             directory, spec["verification_timeout_seconds"], env=env)
        if result.interrupted_signal:
            report["interrupted_signal"] = result.interrupted_signal
        if result.returncode != 0 or result.timed_out or result.error or result.interrupted_signal:
            reason = "assertion deadline exceeded" if result.timed_out else result.error or result.stderr or "assertion worker interrupted or failed"
            return [_check("verification", False, "all assertions completed within the deadline", reason)], False
        if not output.is_file() or output.stat().st_size > 8 * 1024 * 1024:
            return [_check("verification", False, "bounded assertion report", "missing or oversized worker report")], False
        return json.loads(output.read_text(encoding="utf-8")), True


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
        "inputs": [], "verification_complete": False, "interrupted_signal": None,
    }
    checks = report["checks"]
    supervision_error = None
    try:
        with _work_directory() as directory:
            root = Path(directory).resolve()
            report["workdir"] = str(root)
            identities = []
            for source, relative in sources:
                fingerprint, identity = _stage_input(source, root.joinpath(*relative.split("/")))
                report["inputs"].append({"source": str(source), "dest": relative, **fingerprint})
                identities.append(identity)
            argv = [arg.replace("{spec_dir}", str(spec_dir)).replace("{work_dir}", str(root))
                    for arg in spec["argv"]]
            try:
                argv = _executable(argv)
                report["argv"] = argv
                result = run_process(argv, root, spec["timeout_seconds"])
                report.update(exit_code=result.returncode, timed_out=result.timed_out,
                              stdout=result.stdout, stderr=result.stderr,
                              interrupted_signal=result.interrupted_signal)
                report["output_truncated"] = result.truncated
                report["output_incomplete"] = result.incomplete
                report["output_encoding_errors"] = result.encoding_errors
                report["output_bytes_base64"] = result.bytes_base64
                supervision_error = result.error
            except OSError as exc:
                report["error"] = f"cannot start command: {exc}"
                checks.append(_check("spawn", False, "command starts", str(exc)))
                report["output_truncated"] = {"stdout": False, "stderr": False}
            checks.append(_check("timeout", not report["timed_out"], spec["timeout_seconds"], report["timed_out"]))
            checks.append(_check("exit_code", report["exit_code"] == spec["expect"]["exit_code"],
                                 spec["expect"]["exit_code"], report["exit_code"]))
            checks.append(_check("output_capture", not (any(report["output_truncated"].values())
                                 or report.get("output_incomplete") or report.get("output_encoding_errors")),
                                 f"complete UTF-8 output, at most {CAPTURE_LIMIT} bytes per stream",
                                 {"truncated": report["output_truncated"], "incomplete": report.get("output_incomplete", False),
                                  "encoding_errors": report.get("output_encoding_errors", {})}))
            if not report["interrupted_signal"]:
                assertions, report["verification_complete"] = _verify(spec, root, report, identities)
                checks.extend(assertions)
            if destination is not None:
                report["artifacts"] = _save_artifacts(root, spec["expect"]["files"], destination, identities)
    except OSError as exc:
        supervision_error = f"file handling or cleanup failed: {exc}"
    report["duration_seconds"] = round(time.monotonic() - started, 6)
    report["status"] = "passed" if all(check["passed"] for check in checks) else "failed"
    if supervision_error:
        report.update(status="error", error=supervision_error)
    if report["interrupted_signal"]:
        report.update(status="interrupted", error="command or verification interrupted")
    return report
