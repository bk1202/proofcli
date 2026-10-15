"""Run the real CSV exporter through ProofCLI, including retained evidence."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


PROJECT = Path(__file__).resolve().parents[1]
EXAMPLES = PROJECT / "examples" / "export"


class ExportAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="proofcli-export-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def invoke(self, name, *, artifacts=None, report_path=None):
        installed = os.environ.get("PROOFCLI_TEST_INSTALLED") == "1"
        env = os.environ.copy()
        if installed:
            executable = shutil.which("proofcli")
            self.assertIsNotNone(executable, "Installed mode requires proofcli on PATH")
            args = [executable]
            env.pop("PYTHONPATH", None)
        else:
            args = [sys.executable, "-m", "proofcli"]
            env["PYTHONPATH"] = os.pathsep.join(
                [str(PROJECT), env.get("PYTHONPATH", "")]
            )
        args += ["run", str(EXAMPLES / name), "--json"]
        if artifacts is not None:
            args += ["--artifacts", str(artifacts)]
        if report_path is not None:
            args += ["--report", str(report_path)]
        completed = subprocess.run(
            args, cwd=self.root, env=env, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=15,
        )
        try:
            report = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            self.fail("Expected JSON report: stdout=%r stderr=%r (%s)" %
                      (completed.stdout[:2000], completed.stderr[:2000], exc))
        return completed, report

    def check(self, report, name):
        found = [item for item in report["checks"] if item["name"] == name]
        self.assertEqual(len(found), 1, report)
        return found[0]

    def test_real_export_passes_content_checks_and_retains_artifacts(self):
        artifacts = self.root / "evidence"
        report_path = self.root / "report.json"
        completed, report = self.invoke(
            "good.json", artifacts=artifacts, report_path=report_path
        )
        self.assertEqual(completed.returncode, 0, report)
        self.assertEqual(report["status"], "passed", report)
        self.assertEqual(report["exit_code"], 0, report)
        self.assertTrue(self.check(report, "file:report.json:json_contains")["passed"])
        self.assertTrue(self.check(report, "file:report.csv:csv")["passed"])
        self.assertEqual(Path(report["artifacts_dir"]), artifacts.resolve())
        data = json.loads((artifacts / "report.json").read_text(encoding="utf-8"))
        self.assertEqual(data["summary"], {"row_count": 3, "total": "33.75"})
        self.assertEqual([row["customer"] for row in data["rows"]], ["Ada", "Grace", "Linus"])
        self.assertTrue((artifacts / "report.csv").is_file())
        self.assertEqual(json.loads(report_path.read_text(encoding="utf-8")), report)
        self.assertFalse(Path(report["workdir"]).exists())

    def test_false_success_has_exit_zero_and_nonempty_valid_but_wrong_files(self):
        artifacts = self.root / "failed-evidence"
        completed, report = self.invoke("false-success.json", artifacts=artifacts)
        self.assertEqual(completed.returncode, 1, report)
        self.assertEqual(report["status"], "failed", report)
        self.assertEqual(report["exit_code"], 0, report)
        self.assertTrue(self.check(report, "exit_code")["passed"])
        self.assertTrue(self.check(report, "stdout_regex")["passed"])
        self.assertTrue(self.check(report, "file:report.json")["passed"])
        self.assertTrue(self.check(report, "file:report.csv")["passed"])
        self.assertFalse(self.check(report, "file:report.json:json_contains")["passed"])
        self.assertFalse(self.check(report, "file:report.csv:csv")["passed"])
        data = json.loads((artifacts / "report.json").read_text(encoding="utf-8"))
        self.assertEqual(data["summary"]["row_count"], 0)
        self.assertEqual(data["rows"], [])
        self.assertGreater((artifacts / "report.csv").stat().st_size, 0)
        self.assertFalse(Path(report["workdir"]).exists())

    def test_exact_contract_catches_lying_summary_bad_values_and_extra_columns(self):
        for fault in ("missing-record", "wrong-value", "extra-column"):
            with self.subTest(fault=fault):
                completed, report = self.invoke(fault + ".json")
                self.assertEqual(completed.returncode, 1, report)
                self.assertEqual(report["exit_code"], 0)
                self.assertTrue(self.check(report, "file:report.json:json_contains")["passed"])
                self.assertFalse(self.check(report, "file:report.csv:csv")["passed"])
                if fault != "extra-column":
                    self.assertFalse(self.check(report, "file:report.json:json_equals")["passed"])


if __name__ == "__main__":
    unittest.main()
