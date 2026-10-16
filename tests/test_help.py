"""Regression tests for command help, the SPEC shorthand, and usage exit codes."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


PROJECT = Path(__file__).resolve().parents[1]

# These are the user-facing sentences. Top-level help must show each one on the
# same line as its command, and that command's own --help must show it too.
COMMANDS = {
    "run": "Run an argv command and verify its output contract.",
    "validate": "Check a spec's schema without executing its command.",
    "init": "Write a starter spec without executing it.",
}


class HelpTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="proofcli-help-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def invoke(self, arguments):
        installed = os.environ.get("PROOFCLI_TEST_INSTALLED") == "1"
        env = os.environ.copy()
        # argparse wraps help to the terminal width. Pin it so the one-line
        # command list is stable on Windows, macOS, and Linux.
        env["COLUMNS"] = "80"
        if installed:
            executable = shutil.which("proofcli")
            self.assertIsNotNone(executable, "Installed mode requires proofcli on PATH")
            argv = [executable]
            env.pop("PYTHONPATH", None)
        else:
            argv = [sys.executable, "-m", "proofcli"]
            env["PYTHONPATH"] = os.pathsep.join([str(PROJECT), env.get("PYTHONPATH", "")])
        argv.extend(str(item) for item in arguments)
        return subprocess.run(
            argv, cwd=self.root, env=env, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=15,
        )

    def write_spec(self):
        spec = {
            "version": 1,
            "name": "help shorthand",
            "argv": ["{python}", "-c", "print('done')"],
            "expect": {"stdout_regex": "done"},
        }
        path = self.root / "spec.json"
        path.write_text(json.dumps(spec), encoding="utf-8")
        return path

    def test_top_level_help_lists_every_command_with_its_description(self):
        for arguments in (["--help"], ["-h"], ["--json", "--help"]):
            with self.subTest(arguments=arguments):
                result = self.invoke(arguments)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
                text = result.stdout
                self.assertIn("{run,validate,init}", text)
                self.assertIn("The original proofcli SPEC form also works", text)
                self.assertIn("[--artifacts ARTIFACTS] SPEC", text)
                for name, description in COMMANDS.items():
                    matched = [
                        line for line in text.splitlines()
                        if line.strip().startswith(name + " ") and description in line
                    ]
                    self.assertEqual(len(matched), 1, text)

    def test_subcommand_help_is_distinct_and_accurate(self):
        seen = {}
        for name, description in COMMANDS.items():
            result = self.invoke([name, "--help"])
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")
            text = result.stdout
            seen[name] = text
            self.assertTrue(text.startswith("usage: proofcli %s " % name), text)
            before_positionals = text.split("positional arguments:", 1)[0]
            self.assertIn(description, before_positionals)
            for other, other_description in COMMANDS.items():
                if other != name:
                    self.assertNotIn(other_description, text)
        self.assertEqual(len(set(seen.values())), 3)

        def usage_block(text):
            lines = []
            for line in text.splitlines():
                if line == "":
                    break
                lines.append(line)
            return "\n".join(lines)

        self.assertEqual(
            usage_block(seen["run"]),
            "usage: proofcli run [-h] [--version] [--json] [--report REPORT]\n"
            "                    [--artifacts ARTIFACTS]\n"
            "                    spec",
        )
        self.assertEqual(
            usage_block(seen["validate"]),
            "usage: proofcli validate [-h] [--version] [--json] spec",
        )
        self.assertEqual(
            usage_block(seen["init"]),
            "usage: proofcli init [-h] [--version] [--json] [--force] path",
        )
        self.assertIn("replace an existing spec", seen["init"])
        self.assertIn("save the complete JSON report to this path", seen["run"])
        self.assertNotIn("save the complete JSON report", seen["validate"])
        self.assertNotIn("replace an existing spec", seen["validate"])

    def test_help_does_not_execute_a_spec(self):
        path = self.write_spec()
        marker = self.root / "must-not-run"
        path.write_text(json.dumps({
            "version": 1,
            "argv": ["{python}", "-c", "from pathlib import Path; Path(%r).touch(); print('done')" % str(marker)],
            "expect": {"stdout_regex": "done"},
        }), encoding="utf-8")
        for arguments in ([path, "--help"], ["run", path, "--help"], ["validate", path, "--help"]):
            with self.subTest(arguments=arguments):
                result = self.invoke(arguments)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse(marker.exists())

    def test_spec_shorthand_still_runs(self):
        path = self.write_spec()
        shorthand = self.invoke([path, "--json"])
        explicit = self.invoke(["run", path, "--json"])
        self.assertEqual(shorthand.returncode, 0, shorthand.stderr)
        self.assertEqual(explicit.returncode, 0, explicit.stderr)
        shorthand_report = json.loads(shorthand.stdout)
        explicit_report = json.loads(explicit.stdout)
        self.assertEqual(shorthand_report["status"], "passed")
        self.assertEqual(explicit_report["status"], "passed")
        self.assertEqual(shorthand_report["stdout"], explicit_report["stdout"])
        self.assertEqual(shorthand_report["exit_code"], explicit_report["exit_code"])
        self.assertEqual(shorthand_report["schema_version"], 1)
        prefixed = self.invoke(["--json", path])
        self.assertEqual(prefixed.returncode, 0, prefixed.stderr)
        self.assertEqual(json.loads(prefixed.stdout)["status"], "passed")
        human = self.invoke([path])
        self.assertEqual(human.returncode, 0, human.stderr)
        self.assertIn("PASSED", human.stdout)

    def test_help_and_usage_exit_codes_are_unchanged(self):
        for arguments in (
            ["--help"], ["-h"], ["run", "--help"], ["validate", "--help"], ["init", "--help"],
            ["run", "-h"], ["validate", "-h"], ["init", "-h"],
            ["--help", "--version"], ["--json", "--help"],
        ):
            with self.subTest(arguments=arguments):
                result = self.invoke(arguments)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("usage: proofcli", result.stdout)
                self.assertEqual(result.stderr, "")
        version_first = self.invoke(["--version", "--help"])
        self.assertEqual(version_first.returncode, 0, version_first.stderr)
        self.assertIn("ProofCLI", version_first.stdout)
        self.assertNotIn("usage:", version_first.stdout)
        missing = self.root / "missing.json"
        cases = [
            ([], "the following arguments are required: spec"),
            (["run"], "the following arguments are required: spec"),
            (["validate"], "the following arguments are required: spec"),
            (["init"], "the following arguments are required: path"),
            (["--bogus"], "the following arguments are required: spec"),
            (["run", missing, "--art", "x"], "unrecognized arguments: --art"),
            (["--report", "--help"], "argument --report: expected one argument"),
        ]
        for arguments, message in cases:
            with self.subTest(arguments=arguments):
                result = self.invoke(arguments)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertIn(message, result.stderr)
                self.assertTrue(result.stderr.startswith("ERROR: "), result.stderr)
        json_error = self.invoke(["--json"])
        self.assertEqual(json_error.returncode, 2, json_error.stderr)
        self.assertEqual(json_error.stderr, "")
        self.assertEqual(
            json.loads(json_error.stdout)["error"],
            "the following arguments are required: spec",
        )


if __name__ == "__main__":
    unittest.main()
