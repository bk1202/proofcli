"""Black-box checks for CLI authoring, validation, saved reports, and artifacts."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


PROJECT = Path(__file__).resolve().parents[1]


class QualityOfLifeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="proofcli-qol-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def invoke(self, arguments, *, json_output=True):
        installed = os.environ.get("PROOFCLI_TEST_INSTALLED") == "1"
        env = os.environ.copy()
        if installed:
            executable = shutil.which("proofcli")
            self.assertIsNotNone(executable, "Installed mode requires proofcli on PATH")
            argv = [executable]
            env.pop("PYTHONPATH", None)
        else:
            argv = [sys.executable, "-m", "proofcli"]
            env["PYTHONPATH"] = os.pathsep.join(
                [str(PROJECT), env.get("PYTHONPATH", "")]
            )
        argv.extend(str(item) for item in arguments)
        if json_output:
            argv.append("--json")
        result = subprocess.run(
            argv, cwd=self.root, env=env, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=15,
        )
        if not json_output:
            return result
        try:
            return result, json.loads(result.stdout)
        except json.JSONDecodeError:
            self.fail("Expected one JSON report; stdout=%r stderr=%r" %
                      (result.stdout[:2000], result.stderr[:2000]))

    def write_spec(self, code="print('done')", **extra):
        spec = {
            "version": 1, "name": "CLI fixture",
            "argv": ["{python}", "-c", code],
            "expect": {"stdout_regex": "done"},
        }
        spec.update(extra)
        path = self.root / "spec.json"
        path.write_text(json.dumps(spec), encoding="utf-8")
        return path

    def assert_report(self, result, code, status):
        completed, report = result
        self.assertEqual(completed.returncode, code, report)
        self.assertEqual(report["status"], status, report)
        return report

    def marker_spec(self, **extra):
        self.marker = self.root / "command-executed"
        return self.write_spec(
            "from pathlib import Path; Path(%r).touch(); print('done')" % str(self.marker),
            **extra,
        )

    def test_init_writes_a_runnable_spec_without_executing_it(self):
        path = self.root / "nested" / "starter.json"
        report = self.assert_report(self.invoke(["init", path]), 0, "created")
        self.assertEqual(Path(report["path"]), path)
        generated = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(generated["argv"][0], "{python}")
        self.assertIn("text_regex", generated["expect"]["files"][0])
        self.assertFalse((self.root / "output.txt").exists())
        self.assert_report(self.invoke(["run", path]), 0, "passed")

    def test_init_requires_force_to_overwrite(self):
        path = self.root / "existing.json"
        path.write_text("original contents", encoding="utf-8")
        self.assert_report(self.invoke(["init", path]), 2, "error")
        self.assertEqual(path.read_text(encoding="utf-8"), "original contents")
        self.assert_report(self.invoke(["init", path, "--force"]), 0, "created")
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["version"], 1)

    def test_init_human_output_explains_next_command(self):
        result = self.invoke(["init", self.root / "starter.json"], json_output=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("proofcli run", result.stdout)

    def test_validate_does_not_execute_the_command(self):
        path = self.marker_spec()
        report = self.assert_report(self.invoke(["validate", path]), 0, "valid")
        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["spec"], str(path.resolve()))
        self.assertEqual(report["checks"], [])
        self.assertFalse(self.marker.exists())

    def test_validate_human_output_explains_no_execution(self):
        path = self.marker_spec()
        result = self.invoke(["validate", path], json_output=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("no command was executed", result.stdout.lower())
        self.assertFalse(self.marker.exists())

    def test_validate_invalid_spec_reports_error_without_execution(self):
        path = self.marker_spec(expect={"stdout_regex": "[invalid"})
        self.assert_report(self.invoke(["validate", path]), 2, "error")
        self.assertFalse(self.marker.exists())

    def test_explicit_run_and_legacy_form_both_work(self):
        path = self.write_spec()
        legacy = self.assert_report(self.invoke([path]), 0, "passed")
        explicit = self.assert_report(self.invoke(["run", path]), 0, "passed")
        self.assertEqual(legacy["stdout"], explicit["stdout"])
        self.assertEqual(legacy["exit_code"], explicit["exit_code"])

    def test_json_option_can_precede_an_explicit_subcommand(self):
        path = self.write_spec()
        result = self.invoke(["--json", "run", path], json_output=False)
        self.assert_report((result, json.loads(result.stdout)), 0, "passed")

    def test_json_report_is_saved_in_full_and_creates_parent_directory(self):
        path = self.write_spec()
        destination = self.root / "reports" / "run.json"
        report = self.assert_report(self.invoke([
            "run", path, "--report", destination,
        ]), 0, "passed")
        self.assertEqual(json.loads(destination.read_text(encoding="utf-8")), report)
        self.assertIn("artifacts_dir", report)
        self.assertEqual(list(destination.parent.glob(".proofcli-*.tmp")), [])

    def test_report_is_saved_when_displaying_human_output(self):
        path = self.write_spec()
        destination = self.root / "human-report.json"
        destination.write_text("old report", encoding="utf-8")
        result = self.invoke([path, "--report", destination], json_output=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASSED", result.stdout)
        self.assertEqual(json.loads(destination.read_text(encoding="utf-8"))["status"], "passed")

    def test_failed_run_still_saves_a_json_report(self):
        path = self.write_spec(expect={"files": [{"path": "never-created"}]})
        destination = self.root / "failed.json"
        report = self.assert_report(self.invoke([
            "run", path, "--report", destination,
        ]), 1, "failed")
        self.assertEqual(json.loads(destination.read_text(encoding="utf-8")), report)

    def test_report_cannot_overwrite_the_spec_before_execution(self):
        path = self.marker_spec()
        original = path.read_text(encoding="utf-8")
        self.assert_report(self.invoke(["run", path, "--report", path]), 2, "error")
        self.assertFalse(self.marker.exists())
        self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_report_cannot_overwrite_a_hardlink_to_the_spec(self):
        path = self.marker_spec()
        alias = self.root / "spec-alias.json"
        try:
            os.link(path, alias)
        except OSError as exc:
            self.skipTest("Filesystem does not permit hard links: %s" % exc)
        self.assert_report(self.invoke(["run", path, "--report", alias]), 2, "error")
        self.assertFalse(self.marker.exists())

    def test_report_cannot_overwrite_an_input_fixture(self):
        source = self.root / "source.txt"
        source.write_text("keep this fixture", encoding="utf-8")
        path = self.marker_spec(inputs=[{"source": "source.txt", "dest": "input.txt"}])
        self.assert_report(self.invoke(["run", path, "--report", source]), 2, "error")
        self.assertFalse(self.marker.exists())
        self.assertEqual(source.read_text(encoding="utf-8"), "keep this fixture")

    def test_artifacts_preserve_real_output_and_are_named_in_saved_report(self):
        path = self.write_spec(
            "from pathlib import Path; Path('output.txt').write_text('real output'); print('done')",
            expect={"files": [{"path": "output.txt", "text_regex": "^real output$"}]},
        )
        artifacts = self.root / "artifacts"
        destination = self.root / "report.json"
        report = self.assert_report(self.invoke([
            "run", path, "--artifacts", artifacts, "--report", destination,
        ]), 0, "passed")
        self.assertEqual(report["artifacts_dir"], str(artifacts.resolve()))
        self.assertEqual((artifacts / "output.txt").read_text(encoding="utf-8"), "real output")
        self.assertFalse(Path(report["workdir"]).exists())
        self.assertEqual(json.loads(destination.read_text(encoding="utf-8")), report)

    def test_existing_artifacts_directory_is_refused_before_execution(self):
        path = self.marker_spec()
        artifacts = self.root / "already-exists"
        artifacts.mkdir()
        self.assert_report(self.invoke(["run", path, "--artifacts", artifacts]), 2, "error")
        self.assertFalse(self.marker.exists())

    def test_report_cannot_replace_retained_output_before_execution(self):
        path = self.marker_spec(expect={"files": [{"path": "report.json"}]})
        artifacts = self.root / "artifacts"
        self.assert_report(self.invoke([
            "run", path, "--artifacts", artifacts, "--report", artifacts / "report.json",
        ]), 2, "error")
        self.assertFalse(self.marker.exists())
        self.assertFalse(artifacts.exists())

    def test_one_spec_only_and_no_abbreviated_options(self):
        path = self.marker_spec()
        self.assert_report(self.invoke(["run", path, path]), 2, "error")
        self.assertFalse(self.marker.exists())
        self.assert_report(self.invoke(["run", path, "--art", self.root / "artifacts"]), 2, "error")
        self.assertFalse(self.marker.exists())

    def test_help_and_version_remain_available(self):
        for argument in ("--help", "--version"):
            with self.subTest(argument=argument):
                result = self.invoke([argument], json_output=False)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("proofcli", result.stdout.lower())


if __name__ == "__main__":
    unittest.main()
