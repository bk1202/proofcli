"""The release screenshot is a PNG of a real failing run and a real passing run."""

import os
from pathlib import Path
import struct
import runpy
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[1]
tool = runpy.run_path(str(PROJECT / "tools" / "render_release_screenshot.py"))

# Every test in this module. The release-screenshot job fails unless each one ran.
EXPECTED_TESTS = (
    "test_real_runs_keep_their_output_text",
    "test_png_is_deterministic_and_readable",
    "test_unknown_character_is_not_replaced",
    "test_require_render_refuses_to_skip",
    "test_missing_pillow_skips_only_without_require_render",
    "test_render_guard_rejects_skips_and_missing_tests",
)


def _pillow():
    try:
        import PIL  # noqa: F401
    except ImportError:
        return False
    return True


def _require_render():
    return os.environ.get("PROOFCLI_REQUIRE_RENDER") == "1"


def demand_pillow(test, available):
    """Skip the drawing test, or fail it when the release job requires a render."""
    if available:
        return
    message = "Pillow is required to draw the release screenshot"
    if _require_render():
        test.fail(message)
    test.skipTest("Pillow is installed only when building the release image")


def _method_name(test):
    return test.id().rsplit(".", 1)[-1]


def evaluate_render_run(expected, executed, skipped):
    """Return problems. `executed` and `skipped` are method names."""
    expected = tuple(expected)
    problems = []
    if len(executed) != len(expected) or set(executed) != set(expected):
        problems.append(
            f"ran {len(executed)} {sorted(executed)} != expected {len(expected)} {list(expected)}"
        )
    if skipped:
        problems.append(f"skipped {len(skipped)} {sorted(skipped)}")
    return problems


def _chunks(data):
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    pos = 8
    tags = []
    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        tags.append(data[pos + 4:pos + 8])
        pos += 12 + length
    return tags


def _size(data):
    return struct.unpack(">II", data[16:24])


class ReleaseScreenshotTests(unittest.TestCase):
    def test_real_runs_keep_their_output_text(self):
        blocks = tool["capture"]()
        self.assertIn("python -m proofcli run examples/export/wrong-value.json", blocks[0][0])
        self.assertIn("process exit: 1", blocks[0][0])
        self.assertIn("999.00", blocks[0][1])
        self.assertIn("FAILED", blocks[0][1])
        self.assertIn("expected: \"8.25\"", blocks[0][1])
        self.assertIn("python -m proofcli run examples/export/good.json", blocks[1][0])
        self.assertIn("process exit: 0", blocks[1][0])
        self.assertIn("All 9 checks passed.", blocks[1][1])
        self.assertIn("PASSED", blocks[1][1])

    def test_png_is_deterministic_and_readable(self):
        demand_pillow(self, _pillow())
        blocks = tool["capture"]()
        first = tool["render_png"](blocks)
        second = tool["render_png"](blocks)
        self.assertEqual(first, second)
        width, height = _size(first)
        self.assertGreaterEqual(width, 1200)
        self.assertLessEqual(width, 1600)
        self.assertGreater(height, 600)
        tags = _chunks(first)
        for banned in (b"tIME", b"tEXt", b"iTXt", b"zTXt"):
            self.assertNotIn(banned, tags)
        self.assertEqual(tags[0], b"IHDR")
        self.assertEqual(tags[-1], b"IEND")

    def test_unknown_character_is_not_replaced(self):
        with self.assertRaises(ValueError):
            tool["render_png"]([("ok", "caf\u00e9")])

    def test_require_render_refuses_to_skip(self):
        previous = os.environ.get("PROOFCLI_REQUIRE_RENDER")
        os.environ["PROOFCLI_REQUIRE_RENDER"] = "1"
        try:
            with self.assertRaises(AssertionError):
                demand_pillow(self, False)
        finally:
            if previous is None:
                os.environ.pop("PROOFCLI_REQUIRE_RENDER", None)
            else:
                os.environ["PROOFCLI_REQUIRE_RENDER"] = previous

    def test_missing_pillow_skips_only_without_require_render(self):
        previous = os.environ.pop("PROOFCLI_REQUIRE_RENDER", None)
        try:
            with self.assertRaises(unittest.SkipTest):
                demand_pillow(self, False)
        finally:
            if previous is not None:
                os.environ["PROOFCLI_REQUIRE_RENDER"] = previous

    def test_render_guard_rejects_skips_and_missing_tests(self):
        self.assertEqual(evaluate_render_run(EXPECTED_TESTS, EXPECTED_TESTS, []), [])
        problems = evaluate_render_run(
            EXPECTED_TESTS,
            ["test_png_is_deterministic_and_readable"],
            ["test_real_runs_keep_their_output_text"],
        )
        self.assertEqual(len(problems), 2)


class _RecordingResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.executed = []
        self.skipped_names = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.executed.append(_method_name(test))

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.executed.append(_method_name(test))

    def addError(self, test, err):
        super().addError(test, err)
        self.executed.append(_method_name(test))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.skipped_names.append(_method_name(test))


def run_required():
    """Run this module and fail unless every expected test ran and none were skipped."""
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ReleaseScreenshotTests)
    found = [_method_name(test) for test in suite]
    if set(found) != set(EXPECTED_TESTS) or len(found) != len(EXPECTED_TESTS):
        print("Release screenshot tests do not match the expected ids:", file=sys.stderr)
        print(f"  found {found}", file=sys.stderr)
        print(f"  expected {list(EXPECTED_TESTS)}", file=sys.stderr)
        return 1
    runner = unittest.TextTestRunner(verbosity=2, resultclass=_RecordingResult)
    result = runner.run(suite)
    problems = evaluate_render_run(EXPECTED_TESTS, result.executed, result.skipped_names)
    print(
        f"release-screenshot tests: ran {len(result.executed)}, "
        f"skipped {len(result.skipped_names)}, expected {len(EXPECTED_TESTS)}"
    )
    if problems or not result.wasSuccessful():
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    if _require_render():
        sys.exit(run_required())
    unittest.main()
