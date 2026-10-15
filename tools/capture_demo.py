"""Run both sides of the demo and save compact, checked evidence for the video."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    example = ROOT / "examples/export"
    with tempfile.TemporaryDirectory(prefix="proofcli-demo-") as directory:
        stage = Path(directory)
        staged_example = stage / "examples/export"
        (staged_example / "fixtures").mkdir(parents=True)
        for name in ("export.py", "wrong-value.json", "fixtures/input.csv"):
            shutil.copyfile(example / name, staged_example / name)
        report_path = stage / "report.json"
        export_args = ["examples/export/export.py", "examples/export/fixtures/input.csv", "report.json", "--fault", "wrong-value"]
        command = [sys.executable, *export_args]
        ordinary = subprocess.run(command, cwd=directory, capture_output=True, text=True, timeout=10)
        assert ordinary.returncode == 0, ordinary.stderr
        exported = json.loads(report_path.read_text(encoding="utf-8"))
        assert exported["rows"][1]["amount"] == "999.00"
        proof_args = ["-m", "proofcli", "run", "examples/export/wrong-value.json", "--json"]
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        verified = subprocess.run([sys.executable, *proof_args], cwd=stage, env=env,
                                  capture_output=True, text=True, timeout=15)
        assert verified.returncode == 1, verified.stderr
        proof = json.loads(verified.stdout)
        assert proof["status"] == "failed" and proof["exit_code"] == 0 and proof["verification_complete"]
        difference = next(c["actual"]["difference"] for c in proof["checks"]
                          if c["name"].endswith(":json_equals"))
        assert difference["path"] == "$/rows/1/amount" and difference["expected"] == "8.25"
        assert difference["actual"] == exported["rows"][1]["amount"]
        assert len([c for c in proof["checks"] if not c["passed"]]) == 2
        evidence = {"ordinary": {"exit_code": ordinary.returncode, "stdout": ordinary.stdout.strip()},
                    "proofcli": {"status": proof["status"], "exit_code": verified.returncode, "child_exit_code": proof["exit_code"],
                                 "difference": difference},
                    "record": exported["rows"][1],
                    "fixture_sha256": hashlib.sha256((example / "fixtures/input.csv").read_bytes()).hexdigest(),
                    "commands": {"export": "python " + " ".join(export_args), "proofcli": "python " + " ".join(proof_args)},
                    "source_csv": (example / "fixtures/input.csv").read_text(encoding="utf-8"),
                    "output_csv": report_path.with_suffix(".csv").read_text(encoding="utf-8"),
                    "failed_checks": [{"name": c["name"], "difference": c["actual"]["difference"]}
                                      for c in proof["checks"] if not c["passed"]]}
        destination = ROOT / "demo/src/evidence.json"
        destination.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
