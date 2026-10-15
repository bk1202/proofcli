"""Execute the GitHub Action entry point with real contracts and runner files."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]


class ActionTests(unittest.TestCase):
    def test_action_does_not_report_stale_status_when_report_is_protected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = root / "spec.json"
            original = json.dumps({"version": 1, "argv": ["{python}", "-c", "print('ok')"],
                                   "expect": {"stdout_regex": "ok"}})
            spec.write_text(original, encoding="utf-8")
            env = os.environ.copy()
            env.update(PROOFCLI_SPEC=str(spec), PROOFCLI_REPORT=str(spec), PROOFCLI_ARTIFACTS="",
                       RUNNER_TEMP=str(root), GITHUB_OUTPUT=str(root / "outputs"),
                       GITHUB_STEP_SUMMARY=str(root / "summary"))
            result = subprocess.run([sys.executable, PROJECT / ".github/proofcli_action.py"], cwd=root,
                                    env=env, capture_output=True, timeout=15)
            self.assertEqual(result.returncode, 2)
            self.assertIn("\nerror\n", (root / "outputs").read_text(encoding="utf-8"))
            self.assertEqual(spec.read_text(encoding="utf-8"), original)

    def test_action_propagates_pass_failure_and_invalid_spec(self):
        for mode, expected_exit, expected_status in (("pass", 0, "passed"), ("fail", 1, "failed"), ("invalid", 2, "error")):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                spec = root / '--unicode \u96ea $() \' contract.json'
                if mode == "invalid":
                    spec.write_text('{"unknown":true}', encoding="utf-8")
                else:
                    spec.write_text(json.dumps({"version": 1, "argv": ["{python}", "-c", "print('actual')"],
                        "expect": {"stdout_regex": "actual" if mode == "pass" else "promised"}}), encoding="utf-8")
                env = os.environ.copy()
                env.update(PROOFCLI_SPEC=spec.name, PROOFCLI_REPORT="", PROOFCLI_ARTIFACTS="",
                    RUNNER_TEMP=str(root), GITHUB_OUTPUT=str(root / "outputs"),
                    GITHUB_STEP_SUMMARY=str(root / "summary"))
                result = subprocess.run([sys.executable, PROJECT / ".github/proofcli_action.py"], cwd=root,
                                        env=env, capture_output=True, timeout=15)
                self.assertEqual(result.returncode, expected_exit, result.stderr)
                text = (root / "outputs").read_text(encoding="utf-8")
                self.assertIn("\n" + expected_status + "\n", text)
                report = next(root.glob("proofcli-action-*/report.json"))
                self.assertEqual(json.loads(report.read_text(encoding="utf-8"))["status"], expected_status)
                self.assertIn(f"Exit code: {expected_exit}", (root / "summary").read_text(encoding="utf-8"))
