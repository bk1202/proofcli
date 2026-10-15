"""Console entry point; child output is data, never mixed into the report."""

import argparse
import json
import os
import signal
import unicodedata
from pathlib import Path
import sys
import tempfile

from . import __version__
from .runner import error_report, run_spec
from .spec import SpecError, load_spec
from .process import RunInterrupted


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise SpecError(message)


def _display(value):
    return "".join(c if unicodedata.category(c) not in ("Cc", "Cf", "Cs")
                   else c.encode("unicode_escape").decode("ascii") for c in str(value))


def _human(report):
    if report["status"] == "valid":
        return (f"VALID: {_display(report['name'])}\n  Spec: {_display(report['spec'])}\n"
                "  Validation complete; no command was executed.")
    if report["status"] == "created":
        return (f"Created spec: {_display(report['path'])}\n"
                f"  Next: proofcli run \"{_display(report['path'])}\"")
    lines = [f"{report['status'].upper()}: {_display(report['name'])}"]
    if report.get("error"):
        lines.append(f"  Error: {_display(report['error'])}")
    for check in report["checks"]:
        marker = "PASS" if check["passed"] else "FAIL"
        lines.append(f"  [{marker}] {_display(check['name'])}: expected {check['expected']!r}; actual {check['actual']!r}")
    lines.append(f"  Exit: {report['exit_code']}; elapsed: {report['duration_seconds']:.3f}s")
    if report["workdir"]:
        lines.append(f"  Temporary directory (removed): {_display(report['workdir'])}")
    if report.get("artifacts_dir"):
        lines.append(f"  Artifacts: {_display(report['artifacts_dir'])}")
    for stream in ("stdout", "stderr"):
        if report[stream]:
            # Escape controls, including terminal escape sequences from child programs.
            lines.append(f"  {stream}: {json.dumps(report[stream], ensure_ascii=True)}")
    return "\n".join(lines)


def _parser(command, explicit):
    parser = Parser(
        prog="proofcli" + (" " + command if explicit else ""),
        description="Run an argv command and verify its explicit output contract.",
        epilog=("Commands: run SPEC, validate SPEC, init PATH. The original proofcli SPEC form also works.\n"
                "Example: proofcli run contract.json --report verification.json --artifacts evidence\n"
                "Exit: 0 passed, 1 failed/deadline, 2 invalid/I/O, 130 interrupted, 143 SIGTERM.\n"
                "Commands/specs must be trusted. See README for limits and assertion semantics."),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    parser.add_argument("--version", action="version", version=f"ProofCLI {__version__}")
    parser.add_argument("--json", action="store_true", help="emit a single JSON report")
    if command == "init":
        parser.add_argument("path", help="where to create the starter JSON spec")
        parser.add_argument("--force", action="store_true", help="replace an existing spec")
    else:
        parser.add_argument("spec", help="path to a version 1 JSON spec")
        if command == "run":
            parser.add_argument("--report", help="save the complete JSON report to this path")
            parser.add_argument("--artifacts", help="copy generated output into a new directory")
    return parser


def _same_path(first, second):
    if first.resolve() == second.resolve():
        return True
    try:
        return first.samefile(second)
    except FileNotFoundError:
        return False


def _report_path(value, spec_path, spec):
    target = Path(value).resolve()
    protected = [spec_path]
    for item in spec.get("inputs", []):
        protected.append(spec_path.parent / item["source"])
    if any(_same_path(target, path) for path in protected):
        raise SpecError("report path must not overwrite the spec or an input source")
    return target


def _save_report(path, report):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=".proofcli-", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(report, handle, ensure_ascii=True, allow_nan=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _init(path, force):
    # Preserve a final symlink for exclusive creation: even a dangling link exists.
    path = Path(path).absolute()
    spec = {
        "version": 1,
        "name": "Verify generated output",
        "argv": [
            "{python}", "-c",
            "from pathlib import Path; "
            "Path('output.txt').write_bytes(b'ProofCLI verified this output.\\n'); "
            "print('Created output.txt')",
        ],
        "timeout_seconds": 10,
        "expect": {
            "exit_code": 0,
            "stdout_regex": "Created output[.]txt",
            "files": [{
                "path": "output.txt", "min_size": 1,
                "text_regex": "^ProofCLI verified this output[.]\\n$",
            }],
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("w" if force else "x", encoding="utf-8") as handle:
            json.dump(spec, handle, ensure_ascii=True, indent=2)
            handle.write("\n")
    except FileExistsError as exc:
        raise SpecError("spec already exists; use --force to replace it") from exc
    return {"schema_version": 1, "status": "created", "path": str(path)}


def _main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    dispatch = 1 if argv and argv[0] == "--json" else 0
    explicit = bool(len(argv) > dispatch and argv[dispatch] in ("run", "validate", "init"))
    command = argv[dispatch] if explicit else "run"
    parser = _parser(command, explicit)
    tokens = argv[:dispatch] + argv[dispatch+1:] if explicit else argv
    json_output = "--json" in argv
    report_path = None
    report = None
    try:
        args = parser.parse_args(tokens)
        json_output = args.json
        if command == "init":
            report = _init(args.path, args.force)
        else:
            spec_path = Path(args.spec).resolve()
            # Preserve an error report for malformed/missing specs without ever
            # replacing the spec itself. Input protection is added after parsing.
            if command == "run" and args.report:
                report_path = _report_path(args.report, spec_path, {"inputs": []})
            spec = load_spec(spec_path)
            if command == "validate":
                report = {
                    "schema_version": 1, "status": "valid", "name": spec["name"],
                    "spec": str(spec_path), "checks": [],
                }
            else:
                report_path = None
                report_path = _report_path(args.report, spec_path, spec) if args.report else None
                if report_path is not None and args.artifacts:
                    artifact_root = Path(args.artifacts).resolve()
                    for expected in spec["expect"]["files"]:
                        artifact = artifact_root.joinpath(*expected["path"].split("/"))
                        if (_same_path(report_path, artifact) or artifact.is_relative_to(report_path)
                                or artifact_root.is_relative_to(report_path)):
                            report_path = None
                            raise SpecError("report path must not overwrite a retained output artifact")
                report = run_spec(spec, spec_dir=spec_path.parent, artifacts_dir=args.artifacts)
    except (SpecError, OSError, ValueError, RuntimeError) as exc:
        report = error_report(exc)
    except KeyboardInterrupt as exc:
        report = error_report("interrupted")
        report["status"] = "interrupted"
        report["interrupted_signal"] = getattr(exc, "signum", signal.SIGINT)
    if report_path is not None:
        try:
            _save_report(report_path, report)
        except OSError as exc:
            # Preserve execution/check evidence when writing the report fails.
            report.update(status="error", error=f"cannot save report: {exc}")
    code = {
        "passed": 0, "valid": 0, "created": 0,
        "failed": 1, "error": 2, "interrupted": 130,
    }[report["status"]]
    if report["status"] == "interrupted" and report.get("interrupted_signal") == signal.SIGTERM:
        code = 143
    try:
        stream = sys.stderr if code in (2, 130, 143) else sys.stdout
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")
        if json_output:
            print(json.dumps(report, ensure_ascii=True, allow_nan=False), flush=True)
        else:
            print(_human(report), file=stream, flush=True)
    except OSError:
        # A closed pipe or unwritable report destination cannot receive a report.
        return 2
    return code


def main(argv=None):
    def interrupted(signum, frame):
        raise RunInterrupted(signum)
    handlers = {}
    try:
        for signum in (signal.SIGTERM, getattr(signal, "SIGBREAK", signal.SIGINT)):
            try:
                handlers[signum] = signal.signal(signum, interrupted)
            except ValueError:
                # Embedded callers may invoke main outside Python's main thread.
                break
        return _main(argv)
    finally:
        for signum, handler in handlers.items():
            signal.signal(signum, handler)
