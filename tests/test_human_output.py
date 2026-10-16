"""Human-readable report text: failures lead with the difference, success stays short."""

import json
import os
import shutil
import subprocess
import sys
import unittest

import test_cli

PROJECT = test_cli.PROJECT


def _escaped_child_text(text):
    """JSON-escape child text the way the formatter does, including print()'s newline."""
    return json.dumps(text + os.linesep, ensure_ascii=True)


class HumanOutputTests(unittest.TestCase):
    # Reuse the spec/invoke helpers without inheriting (and re-running) ProofCLITests.
    setUp = test_cli.ProofCLITests.setUp
    spec = test_cli.ProofCLITests.spec
    invoke = test_cli.ProofCLITests.invoke
    invoke_path = test_cli.ProofCLITests.invoke_path

    def run_cli(self, *args):
        installed = os.environ.get("PROOFCLI_TEST_INSTALLED") == "1"
        env = os.environ.copy()
        if installed:
            executable = shutil.which("proofcli")
            self.assertIsNotNone(executable, "Installed mode requires proofcli on PATH")
            command = [executable]
            env.pop("PYTHONPATH", None)
        else:
            command = [sys.executable, "-m", "proofcli"]
            env["PYTHONPATH"] = os.pathsep.join([str(PROJECT), env.get("PYTHONPATH", "")])
        return subprocess.run(command + [str(arg) for arg in args], cwd=self.root, env=env,
                              capture_output=True, text=True, encoding="utf-8", timeout=30)

    def test_failed_json_assertion_shows_path_expected_and_actual(self):
        completed = self.run_cli("run", PROJECT / "examples" / "export" / "wrong-value.json")
        self.assertEqual(completed.returncode, 1, completed.stderr)
        out = completed.stdout
        self.assertIn("2 of 9 checks failed:", out)
        self.assertIn("[FAIL] file:report.json:json_equals\n", out)
        self.assertIn("at $/rows/1/amount: value or type differs", out)
        self.assertIn('expected: "8.25"', out)
        self.assertIn('actual:   "999.00"', out)
        self.assertIn("7 other checks passed.", out)
        # No Python reprs and no line dumping the whole expected document.
        self.assertNotIn("'equals': False", out)
        self.assertNotIn("[PASS]", out)
        self.assertLess(max(len(line) for line in out.splitlines()), 200)

    def test_record_count_difference_is_explained(self):
        completed = self.run_cli("run", PROJECT / "examples" / "export" / "false-success.json")
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn("at $/rows: record count differs", completed.stdout)
        self.assertIn("at $/summary/row_count: value or type differs", completed.stdout)

    def test_success_is_concise(self):
        completed = self.run_cli("run", PROJECT / "examples" / "export" / "good.json")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        lines = completed.stdout.splitlines()
        self.assertEqual(lines[0], "PASSED: CSV export acceptance check")
        self.assertEqual(lines[1], "  All 9 checks passed.")
        self.assertTrue(lines[2].startswith("  Command exit code: 0; elapsed: "))
        self.assertTrue(lines[3].startswith("  Temporary directory (removed): "))
        # Child logs stay visible on success, as in earlier releases (Action job logs rely on it).
        # print() ends the line with the platform newline (CRLF on Windows).
        self.assertEqual(lines[4], "  stdout: " + _escaped_child_text(
            "Export complete: report.json and report.csv"))
        self.assertEqual(len(lines), 5, completed.stdout)
        self.assertNotIn("[PASS]", completed.stdout)

    def test_child_logs_are_printed_in_full_on_success(self):
        code = "import sys; print('o' * 500); print('e' * 500, file=sys.stderr)"
        completed = self.invoke(self.spec(code, expect={"stdout_regex": "o"}), json_output=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("  stdout: " + _escaped_child_text("o" * 500), completed.stdout)
        self.assertIn("  stderr: " + _escaped_child_text("e" * 500), completed.stdout)

    def test_exit_code_and_regex_failures_are_readable(self):
        completed = self.invoke(self.spec("import sys; print('hi'); sys.exit(3)",
                                          expect={"exit_code": 0, "stdout_regex": "bye"}),
                                json_output=False)
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn("[FAIL] exit_code\n      expected: 0\n      actual:   3", completed.stdout)
        self.assertIn('no match for regex "bye"', completed.stdout)
        self.assertIn("stdout: " + _escaped_child_text("hi"), completed.stdout)

    def test_timeout_check_shows_limit_and_outcome(self):
        completed = self.invoke(self.spec("import time; time.sleep(10)", timeout_seconds=1),
                                json_output=False)
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn("[FAIL] timeout\n      timed out: exceeded the 1s limit", completed.stdout)
        self.assertIn("; timed out", completed.stdout)
        self.assertNotIn("actual True", completed.stdout)

    def test_passing_timeout_reports_elapsed_against_limit(self):
        from proofcli.cli import _check_details
        report = {"duration_seconds": 0.0712}
        check = {"name": "timeout", "passed": True, "expected": 10, "actual": False}
        self.assertEqual(_check_details(check, report), ["finished in 0.071s (limit 10s)"])

    def test_pre_execution_errors_do_not_show_command_or_exit(self):
        existing = self.root / "evidence"
        existing.mkdir()
        spec = self.root / "spec.json"
        spec.write_text(json.dumps(self.spec()), encoding="utf-8")
        cases = [
            ((), "the following arguments are required: spec"),
            (("run", self.root / "missing.json"), "cannot read spec"),
            (("run", spec, "--artifacts", existing), "artifact directory already exists"),
            (("init", spec), "spec already exists"),
        ]
        for args, message in cases:
            with self.subTest(args=args):
                completed = self.run_cli(*args)
                self.assertEqual(completed.returncode, 2)
                self.assertEqual(completed.stdout, "")
                lines = completed.stderr.splitlines()
                self.assertTrue(lines[0].startswith("ERROR: ") and message in lines[0], completed.stderr)
                self.assertEqual(lines[1:], ["  No command was executed."])
                self.assertNotIn("ERROR: command", completed.stderr)
                self.assertNotIn("Exit: None", completed.stderr)

    def test_json_error_report_is_unchanged(self):
        completed = self.run_cli("--json")
        self.assertEqual(completed.returncode, 2)
        report = json.loads(completed.stdout)
        self.assertEqual(report, {
            "schema_version": 1, "status": "error", "name": "command", "argv": [],
            "exit_code": None, "timed_out": False, "duration_seconds": 0, "workdir": None,
            "stdout": "", "stderr": "", "checks": [],
            "error": "the following arguments are required: spec",
        })

    def test_long_values_are_bounded_and_escaped(self):
        from proofcli.cli import _value
        self.assertTrue(_value("x" * 1000).endswith("..."))
        self.assertLessEqual(len(_value("x" * 1000)), 303)
        self.assertEqual(_value("\x1b[31m"), '"\\u001b[31m"')


if __name__ == "__main__":
    unittest.main()
