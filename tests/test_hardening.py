"""Adversarial regressions using real processes, files, pipes, and signals."""

import hashlib
import base64
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from proofcli.assertions import validate_file_content
from proofcli.spec import SpecError, validate_spec

PROJECT = Path(__file__).resolve().parents[1]


class HardeningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="proofcli-audit-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def spec(self, code="print('done')", **extra):
        result = {"version": 1, "argv": ["{python}", "-c", code], "expect": {"stdout_regex": "done"}}
        result.update(extra)
        return result

    def invoke(self, spec, *options, human=False):
        path = self.root / "contract.json"
        path.write_text(json.dumps(spec), encoding="utf-8")
        env = os.environ.copy()
        if env.get("PROOFCLI_TEST_INSTALLED") == "1":
            command = [shutil.which("proofcli")]
            self.assertIsNotNone(command[0])
            env.pop("PYTHONPATH", None)
        else:
            command = [sys.executable, "-m", "proofcli"]
            env["PYTHONPATH"] = str(PROJECT)
        result = subprocess.run(command + [str(path), *map(str, options)] + ([] if human else ["--json"]),
                                cwd=self.root, env=env, capture_output=True, timeout=12)
        text = result.stdout.decode("utf-8", "replace")
        return result, text if human else json.loads(text)

    def test_output_overflow_stops_a_writer_before_its_sleep(self):
        started = time.monotonic()
        result, report = self.invoke(self.spec(
            "import os,time; os.write(1,b'x'*2097152); time.sleep(5)", timeout_seconds=8,
            expect={"stdout_regex": "x"}))
        self.assertEqual(result.returncode, 1, report)
        self.assertLess(time.monotonic() - started, 4)
        self.assertTrue(report["output_truncated"]["stdout"])
        self.assertLessEqual(len(report["stdout"]), 1048576)

    def test_stderr_overflow_and_dual_streams_do_not_deadlock(self):
        result, report = self.invoke(self.spec(
            "import os; [(os.write(1,b'a'*4096),os.write(2,b'b'*4096)) for _ in range(300)]",
            expect={"stdout_regex": "a", "stderr_regex": "b"}))
        self.assertEqual(result.returncode, 1, report)
        self.assertTrue(any(report["output_truncated"].values()))

    def test_exact_output_limit_is_not_truncation(self):
        result, report = self.invoke(self.spec("import os; os.write(1,b'x'*1048576)", expect={"stdout_regex": "^x+$"}))
        self.assertEqual(result.returncode, 0, report)
        self.assertFalse(report["output_truncated"]["stdout"])

    def test_invalid_utf8_cannot_pass_by_matching_a_replacement_character(self):
        for stream, fd in (("stdout", 1), ("stderr", 2)):
            with self.subTest(stream=stream):
                result, report = self.invoke(self.spec(
                    f"import os; os.write({fd},bytes([255,0,254]))",
                    expect={stream + "_regex": "\ufffd"}))
                self.assertEqual(result.returncode, 1, report)
                self.assertIn(stream, report["output_encoding_errors"])
                self.assertEqual(base64.b64decode(report["output_bytes_base64"][stream]), b"\xff\x00\xfe")
                check = next(c for c in report["checks"] if c["name"] == stream + "_regex")
                self.assertFalse(check["passed"])
                self.assertIn("UTF-8", check["actual"]["error"])

    def test_valid_utf8_replacement_character_and_split_multibyte_output_pass(self):
        result, report = self.invoke(self.spec(
            "import os; os.write(1,('x'*65535+'\u20ac\ufffd').encode('utf-8'))",
            expect={"stdout_regex": "\u20ac\ufffd$"}))
        self.assertEqual(result.returncode, 0, report)
        self.assertEqual(report["output_encoding_errors"], {})
        self.assertEqual(report["output_bytes_base64"], {})

    def test_invalid_utf8_fails_capture_even_without_a_log_assertion(self):
        result, report = self.invoke(self.spec(
            "import os; from pathlib import Path; Path('out').write_text('ok'); os.write(1,b'\\xff')",
            expect={"files": [{"path": "out", "min_size": 2}]}))
        self.assertEqual(result.returncode, 1, report)
        capture = next(c for c in report["checks"] if c["name"] == "output_capture")
        self.assertFalse(capture["passed"])
        self.assertEqual(capture["actual"]["encoding_errors"]["stdout"]["start"], 0)

    @unittest.skipIf(os.name == "nt", "POSIX child-to-parent signal delivery")
    def test_interruption_drains_bytes_written_immediately_before_signal(self):
        # Repeated real delivery exercises scheduling around os.read, including
        # the interval after kernel consumption but before Python assignment.
        for attempt in range(20):
            with self.subTest(attempt=attempt):
                result, report = self.invoke(self.spec(
                    "import os,signal,time; os.write(1,b'last stdout'); os.write(2,b'last stderr'); "
                    "os.kill(os.getppid(),signal.SIGTERM); time.sleep(5)"))
                self.assertEqual(result.returncode, 143, report)
                self.assertEqual(report["stdout"], "last stdout")
                self.assertEqual(report["stderr"], "last stderr")
                self.assertFalse(report["output_incomplete"])

    def test_backtracking_regex_has_an_independent_deadline(self):
        started = time.monotonic()
        result, report = self.invoke(self.spec("print('a'*30+'!')", expect={"stdout_regex": "(a+)+$"},
                                                verification_timeout_seconds=0.3))
        self.assertEqual(result.returncode, 1, report)
        self.assertFalse(report["verification_complete"])
        self.assertLess(time.monotonic() - started, 4)
        self.assertIn("deadline", str(report["checks"]))

    @unittest.skipIf(os.name == "nt", "POSIX custom and ignored signal delivery")
    def test_process_api_preserves_custom_and_ignored_signal_handlers(self):
        from proofcli.process import run_process
        seen = []
        def custom(signum, frame):
            seen.append(signum)
        for signum, handler in ((signal.SIGINT, custom), (signal.SIGTERM, signal.SIG_IGN)):
            with self.subTest(signum=signum):
                previous = signal.signal(signum, handler)
                try:
                    result = run_process([sys.executable, "-c",
                        f"import os,time; os.write(1,b'present'); os.kill(os.getppid(),{int(signum)}); time.sleep(.05)"],
                        self.root, 3)
                    self.assertEqual(result.returncode, 0)
                    self.assertIsNone(result.interrupted_signal)
                    self.assertEqual(result.stdout, "present")
                    self.assertEqual(signal.getsignal(signum), handler)
                finally:
                    signal.signal(signum, previous)
        self.assertEqual(seen, [signal.SIGINT])

    def test_json_rounding_cannot_create_a_false_positive(self):
        result, report = self.invoke(self.spec(
            "from pathlib import Path; Path('out').write_text('{\"n\":1.0000000000000001}')",
            expect={"files": [{"path": "out", "json_contains": {"n": 1.0}}]}))
        self.assertEqual(result.returncode, 1, report)
        mismatch = report["checks"][-1]["actual"]["difference"]
        self.assertEqual(mismatch["path"], "$/n")

    def test_exact_json_catches_unexpected_fields_and_root_arrays(self):
        path = self.root / "out"
        for actual, expected, passed in (("[1,2]", [1, 2], True), ('{"x":1,"extra":2}', {"x": 1}, False),
                                         ('{"rows":[{"id":"2"}]}', {"rows": [{"id": "1"}]}, False)):
            with self.subTest(actual=actual):
                path.write_text(actual, encoding="utf-8")
                check = validate_file_content(path, {"path": "out", "json_equals": expected})[0]
                self.assertEqual(check["passed"], passed)
                if not passed:
                    self.assertIn("difference", check["actual"])

    def test_csv_exact_columns_records_and_values(self):
        path = self.root / "out"
        expected = {"path": "out", "csv": {"columns": ["id", "amount"], "exact_columns": True,
                    "rows": [{"id": "1", "amount": "12.50"}, {"id": "2", "amount": "3.00"}]}}
        for text, passed in (("id,amount\n1,12.50\n2,3.00\n", True),
                             ("id,amount,extra\n1,12.50,x\n2,3.00,y\n", False),
                             ("id,amount\n1,12.50\n", False),
                             ("id,amount\n1,12.50\n2,9.00\n", False),
                             ("id,amount\n1,12.50\n2,3.00\n3,1.00\n", False)):
            with self.subTest(text=text):
                path.write_text(text, encoding="utf-8")
                self.assertEqual(validate_file_content(path, expected)[0]["passed"], passed)

    def test_unicode_input_output_paths_and_fingerprints(self):
        (self.root / "entrée ☕.txt").write_bytes("données".encode())
        spec = self.spec("from pathlib import Path; Path('résultat ☃.txt').write_bytes(Path('entrée.txt').read_bytes())",
                         inputs=[{"source": "entrée ☕.txt", "dest": "entrée.txt"}],
                         expect={"files": [{"path": "résultat ☃.txt", "text_regex": "^données$"}]})
        result, report = self.invoke(spec)
        self.assertEqual(result.returncode, 0, report)
        self.assertEqual(report["inputs"][0]["sha256"], hashlib.sha256("données".encode()).hexdigest())

    def test_portable_shell_punctuation_is_a_literal_output_filename(self):
        name = "a;b$()'[]#.txt"
        result, report = self.invoke(self.spec(
            "from pathlib import Path; Path(%r).write_bytes(b'real')" % name,
            expect={"files": [{"path": name, "text_regex": "^real$"}]}))
        self.assertEqual(result.returncode, 0, report)

    @unittest.skipIf(os.name == "nt", "POSIX special files")
    def test_fifo_output_and_fifo_spec_fail_without_opening_them(self):
        result, report = self.invoke(self.spec("import os; os.mkfifo('out')",
            expect={"files": [{"path": "out", "text_regex": "never"}]}))
        self.assertEqual(result.returncode, 1, report)
        fifo = self.root / "spec.fifo"
        os.mkfifo(fifo)
        env = os.environ.copy()
        if env.get("PROOFCLI_TEST_INSTALLED") == "1":
            command = [shutil.which("proofcli")]
            env.pop("PYTHONPATH", None)
        else:
            command = [sys.executable, "-m", "proofcli"]
            env["PYTHONPATH"] = str(PROJECT)
        result = subprocess.run(command + [str(fifo), "--json"], env=env, cwd=self.root,
                                capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 2)
        self.assertIn("regular file", json.loads(result.stdout)["error"])

    def test_unicode_normalization_alias_and_overlapping_destinations_rejected(self):
        for paths in (("é.txt", "e\u0301.txt"), ("parent", "parent/child")):
            with self.subTest(paths=paths), self.assertRaises(SpecError):
                validate_spec(self.spec(inputs=[{"source": "a", "dest": paths[0]}],
                                        expect={"files": [{"path": paths[1]}, {"path": paths[0]}]}))
        with self.assertRaises(SpecError):
            validate_spec(self.spec(inputs=[{"source": "a", "dest": "é.txt"}],
                                    expect={"files": [{"path": "e\u0301.txt"}]}))

    def test_lone_surrogates_and_windows_device_aliases_are_rejected(self):
        for value in ("\ud800", "CONIN$", "COM¹.txt", "NUL .txt"):
            with self.subTest(value=repr(value)), self.assertRaises(SpecError):
                validate_spec(self.spec(expect={"files": [{"path": value}]}))

    def test_human_report_does_not_emit_terminal_controls(self):
        result, text = self.invoke(self.spec(name="bad\x1b[31m\nname"), human=True)
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("\x1b", text)
        self.assertIn("\\x1b", text)

    def test_oversized_spec_is_rejected_and_error_report_is_saved(self):
        path = self.root / "huge.json"
        path.write_text(" " * (1048576 + 1), encoding="utf-8")
        # Use a real separate entry point, so no malformed-spec helper rewrites it.
        env = os.environ.copy()
        if env.get("PROOFCLI_TEST_INSTALLED") == "1":
            command = [shutil.which("proofcli")]
            env.pop("PYTHONPATH", None)
        else:
            command = [sys.executable, "-m", "proofcli"]
            env["PYTHONPATH"] = str(PROJECT)
        target = self.root / "error.json"
        result = subprocess.run(command + [str(path), "--json", "--report", str(target)],
                                cwd=self.root, env=env, capture_output=True, timeout=5)
        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 2)
        self.assertIn("byte limit", report["error"])
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")), report)

    def test_unrepresentable_spec_decimal_is_rejected_instead_of_rounded(self):
        from proofcli.spec import strict_json_loads
        with self.assertRaisesRegex(SpecError, "precision"):
            strict_json_loads('{"value":1.0000000000000001}')

    def test_exit_code_255_is_not_treated_as_success(self):
        result, report = self.invoke(self.spec("import sys; print('done'); sys.exit(255)"))
        self.assertEqual(result.returncode, 1, report)
        self.assertEqual(report["exit_code"], 255)

    @unittest.skipIf(os.name == "nt", "POSIX signal exit status")
    def test_child_signal_exit_is_reported_as_negative_signal(self):
        result, report = self.invoke(self.spec("import os,signal; os.kill(os.getpid(),signal.SIGTERM)"))
        self.assertEqual(result.returncode, 1, report)
        self.assertEqual(report["exit_code"], -signal.SIGTERM)

    def test_hardlink_to_staged_input_is_not_a_fresh_output(self):
        (self.root / "fixture").write_bytes(b"stale")
        try:
            os.link(self.root / "fixture", self.root / "probe")
        except OSError as exc:
            self.skipTest(str(exc))
        result, report = self.invoke(self.spec(
            "import os; os.link('input','output')", inputs=[{"source": "fixture", "dest": "input"}],
            expect={"files": [{"path": "output"}]}))
        self.assertEqual(result.returncode, 1, report)
        self.assertIn("aliases a staged input", str(report["checks"]))

    def test_broken_report_destination_keeps_execution_evidence(self):
        directory = self.root / "report-dir"
        directory.mkdir()
        result, report = self.invoke(self.spec(), "--report", directory)
        self.assertEqual(result.returncode, 2, report)
        self.assertEqual(report["exit_code"], 0)
        self.assertTrue(report["checks"])
        self.assertIn("cannot save", report["error"])

    def test_normal_parent_exit_stops_an_ordinary_descendant(self):
        marker = self.root / "orphan-survived"
        child = "import time; from pathlib import Path; time.sleep(1.5); Path(%r).touch()" % str(marker)
        result, report = self.invoke(self.spec(
            "import subprocess,sys; subprocess.Popen([sys.executable,'-c',%r]); print('done')" % child))
        self.assertEqual(result.returncode, 0, report)
        time.sleep(1.7)
        self.assertFalse(marker.exists())

    @unittest.skipIf(os.name == "nt", "POSIX detached sessions")
    def test_detached_pipe_holder_cannot_hang_verification(self):
        child = "import time; time.sleep(2)"
        started = time.monotonic()
        result, report = self.invoke(self.spec(
            "import subprocess,sys; subprocess.Popen([sys.executable,'-c',%r],start_new_session=True); print('done')" % child))
        self.assertEqual(result.returncode, 1, report)
        self.assertTrue(report["output_incomplete"])
        self.assertLess(time.monotonic()-started, 2)

    def test_symlink_to_staged_input_cannot_count_as_output(self):
        source = self.root / "fixture"
        source.write_text("stale", encoding="utf-8")
        probe = self.root / "probe-link"
        try:
            probe.symlink_to(source)
        except OSError as exc:
            self.skipTest(str(exc))
        result, report = self.invoke(self.spec(
            "from pathlib import Path; Path('out').symlink_to('input')",
            inputs=[{"source": "fixture", "dest": "input"}], expect={"files": [{"path": "out"}]}))
        self.assertEqual(result.returncode, 1, report)
        self.assertIn("symlink", str(report["checks"]))

    def test_signal_interruption_saves_a_report_and_cleans_workdir(self):
        marker = self.root / "started"
        path = self.root / "signal-spec.json"
        report_path = self.root / "interrupted.json"
        path.write_text(json.dumps(self.spec(
            "from pathlib import Path; import time; Path(%r).touch(); print('started',flush=True); time.sleep(5)" % str(marker),
            expect={"stdout_regex": "started"})), encoding="utf-8")
        wrapper = (
            "import signal,threading,time,sys; from pathlib import Path; from proofcli.cli import main\n"
            "def stop():\n"
            " deadline=time.monotonic()+4\n"
            " while not Path(%r).exists() and time.monotonic()<deadline: time.sleep(.01)\n"
            " signal.raise_signal(signal.SIGTERM)\n"
            "threading.Thread(target=stop,daemon=True).start()\n"
            "sys.exit(main(%r))" % (str(marker), [str(path), "--json", "--report", str(report_path)])
        )
        env = os.environ.copy()
        if env.get("PROOFCLI_TEST_INSTALLED") != "1":
            env["PYTHONPATH"] = str(PROJECT)
        else:
            env.pop("PYTHONPATH", None)
        result = subprocess.run([sys.executable, "-c", wrapper], cwd=self.root, env=env, capture_output=True, timeout=10)
        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 143, report)
        self.assertEqual(report["status"], "interrupted")
        self.assertEqual(report["stdout"], "started\n" if os.name != "nt" else "started\r\n")
        self.assertEqual(json.loads(report_path.read_text(encoding="utf-8")), report)
        self.assertFalse(Path(report["workdir"]).exists())


if __name__ == "__main__":
    unittest.main()
