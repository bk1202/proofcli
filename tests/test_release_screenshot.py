"""The release screenshot is a PNG of a real failing run and a real passing run."""

from pathlib import Path
import struct
import runpy
import unittest

PROJECT = Path(__file__).resolve().parents[1]
tool = runpy.run_path(str(PROJECT / "tools" / "render_release_screenshot.py"))


def _pillow():
    try:
        import PIL  # noqa: F401
    except ImportError:
        return False
    return True


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
        if not _pillow():
            self.skipTest("Pillow is installed only when building the release image")
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


if __name__ == "__main__":
    unittest.main()
