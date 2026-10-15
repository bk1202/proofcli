"""Run both sides of the demo and save compact, checked evidence for the video."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    example = ROOT / "examples/export"
    with tempfile.TemporaryDirectory(prefix="proofcli-demo-") as directory:
        report_path = Path(directory) / "report.json"
        command = [sys.executable, str(example / "export.py"), str(example / "fixtures/input.csv"),
                   str(report_path), "--fault", "wrong-value"]
        ordinary = subprocess.run(command, cwd=directory, capture_output=True, text=True, timeout=10)
        assert ordinary.returncode == 0, ordinary.stderr
        exported = json.loads(report_path.read_text(encoding="utf-8"))
        assert exported["rows"][1]["amount"] == "999.00"
        verified = subprocess.run([sys.executable, "-m", "proofcli", "run", str(example / "wrong-value.json"), "--json"],
                                  cwd=ROOT, capture_output=True, text=True, timeout=15)
        assert verified.returncode == 1, verified.stderr
        proof = json.loads(verified.stdout)
        assert proof["status"] == "failed" and proof["exit_code"] == 0 and proof["verification_complete"]
        difference = next(c["actual"]["difference"] for c in proof["checks"]
                          if c["name"].endswith(":json_equals"))
        assert difference["path"] == "$/rows/1/amount" and difference["expected"] == "8.25"
        evidence = {"ordinary": {"exit_code": ordinary.returncode, "stdout": ordinary.stdout.strip()},
                    "proofcli": {"status": proof["status"], "exit_code": verified.returncode, "child_exit_code": proof["exit_code"],
                                 "difference": difference},
                    "record": exported["rows"][1],
                    "fixture_sha256": hashlib.sha256((example / "fixtures/input.csv").read_bytes()).hexdigest()}
        destination = ROOT / "demo/src/evidence.json"
        destination.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
