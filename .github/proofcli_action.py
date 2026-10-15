"""Run the source bundled with this action, without installing build dependencies."""

import html
import os
from pathlib import Path
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from proofcli.cli import main


def output(name, value):
    delimiter = uuid.uuid4().hex
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as handle:
        handle.write(f"{name}<<{delimiter}\n{value}\n{delimiter}\n")


def run():
    report_input = os.environ.get("PROOFCLI_REPORT", "")
    if report_input:
        report = Path(report_input).absolute()
    else:
        report = Path(tempfile.mkdtemp(prefix="proofcli-action-", dir=os.environ["RUNNER_TEMP"])) / "report.json"
    argv = ["run", "--report", str(report)]
    artifacts = os.environ.get("PROOFCLI_ARTIFACTS", "")
    if artifacts:
        argv.extend(["--artifacts", artifacts])
    argv.extend(["--", os.environ["PROOFCLI_SPEC"]])
    code = main(argv)
    # Never read an existing destination as evidence: a protected path or failed
    # write can leave old bytes there. The run's exit code remains authoritative.
    status = {0: "passed", 1: "failed", 2: "error", 130: "interrupted", 143: "interrupted"}[code]
    output("report", str(report))
    output("status", status)
    output("exit-code", str(code))
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as handle:
        handle.write(f"### ProofCLI: {html.escape(status)}\n\nExit code: {code}. "
                     "The JSON report contains assertion details and captured logs.\n")
    return code


if __name__ == "__main__":
    sys.exit(run())
