"""The package version, README pins and Action references must agree."""

from pathlib import Path
import runpy
import shutil
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
check = runpy.run_path(str(PROJECT / "tools" / "check_versions.py"))["check"]


class VersionAgreementTests(unittest.TestCase):
    def copy(self):
        temp = tempfile.TemporaryDirectory(prefix="proofcli-versions-")
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        for name in ("pyproject.toml", "README.md"):
            shutil.copy2(PROJECT / name, root / name)
        shutil.copytree(PROJECT / "docs", root / "docs", ignore=shutil.ignore_patterns("*.png"))
        (root / "proofcli").mkdir()
        shutil.copy2(PROJECT / "proofcli" / "__init__.py", root / "proofcli" / "__init__.py")
        return root

    def test_repository_versions_agree(self):
        self.assertEqual(check(PROJECT), [])

    def test_mismatches_are_reported(self):
        root = self.copy()
        init = root / "proofcli" / "__init__.py"
        init.write_text('__version__ = "9.9.9"\n', encoding="utf-8")
        readme = root / "README.md"
        text = readme.read_text(encoding="utf-8")
        text = text.replace("proofcli==", "proofcli==0.0.1 # was ", 1)
        text = text.replace("bk1202/proofcli@v", "bk1202/proofcli@v0.0.1 # was ", 1)
        readme.write_text(text, encoding="utf-8")
        problems = "\n".join(check(root))
        self.assertIn("__version__ '9.9.9'", problems)
        self.assertIn("pip pin 0.0.1", problems)
        self.assertIn("Action pin 0.0.1", problems)

    def test_hard_coded_workflow_release_tag_fails(self):
        root = self.copy()
        workflow = root / ".github" / "workflows"
        workflow.mkdir(parents=True)
        (workflow / "demo-video.yml").write_text(
            "gh release upload v0.4.1 motion-demos/*\n"
            "https://github.com/bk1202/proofcli/releases/download/v0.4.1/reel.mp4\n",
            encoding="utf-8",
        )
        problems = "\n".join(check(root))
        self.assertIn(".github/workflows/demo-video.yml:1: release tag v0.4.1", problems)
        self.assertIn(".github/workflows/demo-video.yml:2: release tag v0.4.1", problems)

    def test_missing_pins_fail_closed(self):
        root = self.copy()
        (root / "README.md").write_text("no pins here\n", encoding="utf-8")
        shutil.rmtree(root / "docs")
        self.assertTrue(any("no documented" in p for p in check(root)))


if __name__ == "__main__":
    unittest.main()
