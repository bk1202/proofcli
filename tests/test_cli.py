"""Exercise the installed interface with real child processes and real files."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest


PROJECT = Path(__file__).resolve().parents[1]


class ProofCLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="proofcli-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.counter = 0

    def spec(self, code="print('done')", **overrides):
        value = {
            "version": 1,
            "argv": ["{python}", "-c", code],
            "expect": {"stdout_regex": "done"},
        }
        value.update(overrides)
        return value

    def invoke(self, spec, *, json_output=True, extra_env=None):
        self.counter += 1
        spec_path = self.root / ("spec-%d.json" % self.counter)
        spec_path.write_text(json.dumps(spec), encoding="utf-8")
        return self.invoke_path(spec_path, json_output=json_output, extra_env=extra_env)

    def invoke_path(self, spec_path, *, json_output=True, extra_env=None):
        installed = os.environ.get("PROOFCLI_TEST_INSTALLED") == "1"
        if installed:
            executable = shutil.which("proofcli")
            self.assertIsNotNone(executable, "Installed mode requires proofcli on PATH")
            args = [executable, str(spec_path)]
        else:
            args = [sys.executable, "-m", "proofcli", str(spec_path)]
        if json_output:
            args.append("--json")
        env = os.environ.copy()
        if installed:
            env.pop("PYTHONPATH", None)
        else:
            env["PYTHONPATH"] = os.pathsep.join(
                [str(PROJECT / "src"), str(PROJECT), env.get("PYTHONPATH", "")]
            )
        if extra_env:
            env.update(extra_env)
        completed = subprocess.run(
            args, cwd=self.root if installed else PROJECT, env=env, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=15,
        )
        if not json_output:
            return completed
        try:
            report = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            self.fail("CLI did not emit one JSON report: %r; stderr=%r (%s)" %
                      (completed.stdout[:2000], completed.stderr[:2000], exc))
        return completed, report

    def assert_status(self, result, returncode, status):
        completed, report = result
        self.assertEqual(completed.returncode, returncode, report)
        self.assertEqual(report["status"], status, report)
        return report

    def check(self, report, name):
        found = [item for item in report["checks"] if item["name"] == name]
        self.assertEqual(len(found), 1, report)
        return found[0]

    def assert_invalid_before_execution(self, mutate):
        marker = self.root / "must-not-execute.txt"
        spec = self.spec(
            "from pathlib import Path; Path(%r).write_text('executed'); print('done')"
            % str(marker)
        )
        mutate(spec)
        self.assert_status(self.invoke(spec), 2, "error")
        self.assertFalse(marker.exists(), "Invalid spec executed its command")

    def test_success_reports_real_output_and_removes_workdir(self):
        code = (
            "from pathlib import Path; "
            "Path('nested').mkdir(); "
            "Path('nested/result.txt').write_text('proof', encoding='utf-8'); "
            "print('created result')"
        )
        report = self.assert_status(self.invoke(self.spec(
            code, name="real artifact", expect={
                "stdout_regex": "created result",
                "files": [{"path": "nested/result.txt", "min_size": 5}],
            },
        )), 0, "passed")
        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["name"], "real artifact")
        self.assertEqual(report["exit_code"], 0)
        self.assertFalse(report["timed_out"])
        self.assertEqual(report["stdout"].strip(), "created result")
        self.assertEqual(report["stderr"], "")
        self.assertGreaterEqual(report["duration_seconds"], 0)
        self.assertIsInstance(report["argv"], list)
        self.assertTrue(Path(report["workdir"]).is_absolute())
        self.assertFalse(Path(report["workdir"]).exists())
        for check in report["checks"]:
            self.assertIn("expected", check)
            self.assertIn("actual", check)
            self.assertTrue(check["passed"], check)

    def test_false_success_exit_zero_does_not_prove_artifact(self):
        report = self.assert_status(self.invoke(self.spec(
            "print('Export complete')", expect={
                "stdout_regex": "Export complete",
                "files": [{"path": "export.csv", "min_size": 1}],
            },
        )), 1, "failed")
        self.assertEqual(report["exit_code"], 0)
        self.assertTrue(self.check(report, "stdout_regex")["passed"])
        self.assertFalse(self.check(report, "file:export.csv")["passed"])
        self.assertFalse(Path(report["workdir"]).exists())

    def test_undersized_file_fails(self):
        report = self.assert_status(self.invoke(self.spec(
            "from pathlib import Path; Path('out.bin').write_bytes(b'ab')",
            expect={"files": [{"path": "out.bin", "min_size": 3}]},
        )), 1, "failed")
        self.assertFalse(self.check(report, "file:out.bin")["passed"])

    def test_minimum_size_counts_bytes(self):
        self.assert_status(self.invoke(self.spec(
            "from pathlib import Path; Path('out.bin').write_bytes(bytes([195,169]))",
            expect={"files": [{"path": "out.bin", "min_size": 2}]},
        )), 0, "passed")

    def test_existing_empty_file_passes_default_minimum(self):
        self.assert_status(self.invoke(self.spec(
            "from pathlib import Path; Path('empty.txt').touch()",
            expect={"files": [{"path": "empty.txt"}]},
        )), 0, "passed")

    def test_directory_does_not_satisfy_file_assertion(self):
        report = self.assert_status(self.invoke(self.spec(
            "from pathlib import Path; Path('result').mkdir()",
            expect={"files": [{"path": "result"}]},
        )), 1, "failed")
        self.assertFalse(self.check(report, "file:result")["passed"])

    def test_expected_nonzero_exit_can_pass(self):
        report = self.assert_status(self.invoke(self.spec(
            "import sys; print('expected rejection', file=sys.stderr); sys.exit(7)",
            expect={"exit_code": 7, "stderr_regex": "expected rejection"},
        )), 0, "passed")
        self.assertEqual(report["exit_code"], 7)
        self.assertTrue(self.check(report, "exit_code")["passed"])

    def test_unexpected_nonzero_exit_fails_even_with_matching_output(self):
        report = self.assert_status(self.invoke(self.spec(
            "import sys; print('done'); sys.exit(4)"
        )), 1, "failed")
        self.assertFalse(self.check(report, "exit_code")["passed"])
        self.assertTrue(self.check(report, "stdout_regex")["passed"])

    def test_stdout_and_stderr_are_checked_independently(self):
        code = "import sys; print('OUT'); print('ERR', file=sys.stderr)"
        report = self.assert_status(self.invoke(self.spec(
            code, expect={"stdout_regex": "^OUT", "stderr_regex": "^ERR"},
        )), 0, "passed")
        self.assertEqual(report["stdout"].strip(), "OUT")
        self.assertEqual(report["stderr"].strip(), "ERR")
        report = self.assert_status(self.invoke(self.spec(
            code, expect={"stderr_regex": "OUT"},
        )), 1, "failed")
        self.assertFalse(self.check(report, "stderr_regex")["passed"])

    def test_regex_mismatch_fails(self):
        report = self.assert_status(self.invoke(self.spec(
            "print('almost')", expect={"stdout_regex": "promised"},
        )), 1, "failed")
        self.assertFalse(self.check(report, "stdout_regex")["passed"])

    def test_real_timeout_fails_and_cleans_workdir(self):
        started = time.monotonic()
        report = self.assert_status(self.invoke(self.spec(
            "import time; print('started', flush=True); time.sleep(5)",
            timeout_seconds=0.5, expect={"stdout_regex": "started"},
        )), 1, "failed")
        self.assertLess(time.monotonic() - started, 5)
        self.assertTrue(report["timed_out"])
        self.assertFalse(self.check(report, "timeout")["passed"])
        self.assertFalse(Path(report["workdir"]).exists())

    def test_missing_executable_is_execution_failure(self):
        report = self.assert_status(self.invoke(self.spec(
            argv=["proofcli-no-such-executable-8a48681"],
        )), 1, "failed")
        self.assertFalse(report["timed_out"])
        self.assertFalse(Path(report["workdir"]).exists())

    def test_timeout_stops_an_ordinary_descendant(self):
        ready = self.root / "child-ready"
        release = self.root / "child-release"
        escaped = self.root / "child-survived"
        # If cleanup fails, this child exits on its own after at most four seconds.
        child = (
            "from pathlib import Path; import time; "
            "Path(%r).touch(); deadline=time.monotonic()+4; "
            "release=Path(%r); escaped=Path(%r)\n"
            "while time.monotonic()<deadline:\n"
            " if release.exists():\n"
            "  escaped.touch(); break\n"
            " time.sleep(0.01)\n"
        ) % (str(ready), str(release), str(escaped))
        parent = (
            "import subprocess,sys,time; "
            "subprocess.Popen([sys.executable,'-c',%r]); "
            "print('spawned',flush=True); time.sleep(5)"
        ) % child
        self.assert_status(self.invoke(self.spec(
            parent, timeout_seconds=1.5, expect={"stdout_regex": "spawned"},
        )), 1, "failed")
        self.assertTrue(ready.exists(), "Descendant did not start before timeout")
        release.touch()
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline and not escaped.exists():
            time.sleep(0.02)
        self.assertFalse(escaped.exists(), "Descendant survived command timeout")

    def test_argv_shell_metacharacters_remain_literal(self):
        literal = "hello ; echo INJECTED && $HOME | > output.txt & (x)"
        self.assert_status(self.invoke(self.spec(
            argv=["{python}", "-c", "import sys; print(sys.argv[1])", literal],
            expect={"stdout_regex": "^" + re.escape(literal) + r"\s*$"},
        )), 0, "passed")

    @unittest.skipUnless(os.name == "nt", "Windows batch-file execution rules")
    def test_windows_batch_paths_rejected_even_when_pathext_omits_them(self):
        marker = self.root / "batch-executed.txt"
        for suffix in (".cmd", ".BAT"):
            with self.subTest(suffix=suffix):
                command = self.root / ("must-not-run" + suffix)
                command.write_text('@echo done > "%s"\n' % marker, encoding="utf-8")
                self.assert_status(self.invoke(self.spec(
                    argv=[str(command)],
                ), extra_env={"PATHEXT": ".EXE"}), 2, "error")
                self.assertFalse(marker.exists(), "Batch file was implicitly run by a shell")

    @unittest.skipUnless(os.name == "nt", "Windows batch-file execution rules")
    def test_windows_path_alias_resolving_to_batch_file_is_rejected(self):
        marker = self.root / "alias-executed.txt"
        alias = "proofcli-test-batch-alias-6f2d"
        command = self.root / (alias + ".cmd")
        command.write_text('@echo done > "%s"\n' % marker, encoding="utf-8")
        path = str(self.root) + os.pathsep + os.environ.get("PATH", "")
        self.assert_status(self.invoke(self.spec(argv=[alias]), extra_env={
            "PATH": path, "PATHEXT": ".CMD;.EXE",
        }), 2, "error")
        self.assertFalse(marker.exists(), "PATH alias implicitly ran a batch file")

    def test_workdir_is_empty_and_does_not_copy_spec_neighbors(self):
        (self.root / "existing.txt").write_text("not an output", encoding="utf-8")
        report = self.assert_status(self.invoke(self.spec(
            "from pathlib import Path; print(list(Path('.').iterdir()))",
            expect={"stdout_regex": r"^\[\]\s*$"},
        )), 0, "passed")
        self.assertNotEqual(Path(report["workdir"]), self.root)

    def test_fresh_workdir_cannot_reuse_previous_output(self):
        first = self.spec(
            "from pathlib import Path; Path('result').write_text('yes')",
            expect={"files": [{"path": "result"}]},
        )
        first_report = self.assert_status(self.invoke(first), 0, "passed")
        second = self.spec("pass", expect={"files": [{"path": "result"}]})
        second_report = self.assert_status(self.invoke(second), 1, "failed")
        self.assertNotEqual(first_report["workdir"], second_report["workdir"])

    def test_unknown_keys_rejected_before_execution(self):
        for location in ("top", "expect", "file"):
            with self.subTest(location=location):
                def mutate(spec):
                    if location == "top":
                        spec["typo"] = True
                    elif location == "expect":
                        spec["expect"]["stdout_regx"] = "done"
                    else:
                        spec["expect"]["files"] = [{"path": "x", "minimum": 1}]
                self.assert_invalid_before_execution(mutate)

    def test_invalid_argv_rejected_before_execution(self):
        for argv in ([], "python -c pass", [1], [""], [True]):
            with self.subTest(argv=argv):
                self.assert_invalid_before_execution(lambda spec: spec.update(argv=argv))

    def test_invalid_version_rejected_before_execution(self):
        for version in (0, 2, True, "1", None):
            with self.subTest(version=version):
                self.assert_invalid_before_execution(lambda spec: spec.update(version=version))

    def test_invalid_exit_code_rejected_before_execution(self):
        for exit_code in (True, "0", 0.5, None):
            with self.subTest(exit_code=exit_code):
                self.assert_invalid_before_execution(lambda spec: spec.update(
                    expect={"exit_code": exit_code, "stdout_regex": "done"}
                ))

    def test_unreadable_or_malformed_spec_is_a_json_error(self):
        self.assert_status(self.invoke_path(self.root / "missing.json"), 2, "error")
        path = self.root / "malformed.json"
        for text in ('{broken json', '{"version":1,"version":2}'):
            with self.subTest(text=text):
                path.write_text(text, encoding="utf-8")
                self.assert_status(self.invoke_path(path), 2, "error")

    def test_invalid_timeout_rejected_before_execution(self):
        for timeout in (0, -1, True, "1", float("inf"), float("nan")):
            with self.subTest(timeout=timeout):
                self.assert_invalid_before_execution(
                    lambda spec: spec.update(timeout_seconds=timeout)
                )

    def test_meaningful_assertion_required_before_execution(self):
        for expect in ({}, {"exit_code": 0}, {"stdout_regex": ""}, {"files": []}):
            with self.subTest(expect=expect):
                self.assert_invalid_before_execution(lambda spec: spec.update(expect=expect))

    def test_invalid_regex_rejected_before_execution(self):
        for field in ("stdout_regex", "stderr_regex"):
            for pattern in ("[unterminated", "a{99999999999999999999}"):
                with self.subTest(field=field, pattern=pattern):
                    self.assert_invalid_before_execution(
                        lambda spec: spec.update(expect={field: pattern})
                    )

    def test_unsafe_paths_rejected_before_execution(self):
        for path in ("../escape", "a/../escape", "/absolute", "C:/absolute", "a\\b", ""):
            with self.subTest(path=path):
                self.assert_invalid_before_execution(lambda spec: spec.update(
                    expect={"files": [{"path": path}]}
                ))

    def test_invalid_minimum_size_rejected_before_execution(self):
        for size in (-1, 1.5, True, "1"):
            with self.subTest(size=size):
                self.assert_invalid_before_execution(lambda spec: spec.update(
                    expect={"files": [{"path": "x", "min_size": size}]}
                ))

    def test_human_report_is_readable(self):
        completed = self.invoke(self.spec(name="human check"), json_output=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("human check", completed.stdout)
        self.assertRegex(completed.stdout.lower(), "pass")

    def test_excessive_output_is_bounded_and_fails(self):
        report = self.assert_status(self.invoke(self.spec(
            "import sys; sys.stdout.write('x' * (1024 * 1024 + 1024))",
            expect={"stdout_regex": "x"},
        )), 1, "failed")
        self.assertLessEqual(len(report["stdout"].encode("utf-8")), 1024 * 1024)
        self.assertFalse(self.check(report, "output_capture")["passed"])


if __name__ == "__main__":
    unittest.main()
