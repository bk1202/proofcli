"""The release screenshot is a PNG of a real failing run and a real passing run."""

from pathlib import Path
import struct
import runpy
import unittest
import zlib

PROJECT = Path(__file__).resolve().parents[1]
tool = runpy.run_path(str(PROJECT / "tools" / "render_release_screenshot.py"))


def _decoded(data):
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    pos = 8
    width = height = None
    compressed = b""
    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if tag == b"IHDR":
            width, height = struct.unpack(">II", chunk[:8])
        elif tag == b"IDAT":
            compressed += chunk
        elif tag == b"IEND":
            break
    raw = zlib.decompress(compressed)
    stride = width * 3 + 1
    foreground = heading = 0
    fg = bytes(tool["FG"])
    hd = bytes(tool["HEADING"])
    for y in range(height):
        row = raw[y * stride + 1:(y + 1) * stride]
        for x in range(width):
            pixel = row[x * 3:x * 3 + 3]
            if pixel == fg:
                foreground += 1
            elif pixel == hd:
                heading += 1
    return width, height, foreground, heading


class ReleaseScreenshotTests(unittest.TestCase):
    def test_real_runs_are_drawn_without_clipping(self):
        blocks = tool["capture"]()
        self.assertIn("process exit: 1", blocks[0][0])
        self.assertIn("999.00", blocks[0][1])
        self.assertIn("FAILED", blocks[0][1])
        self.assertIn("process exit: 0", blocks[1][0])
        self.assertIn("All 9 checks passed.", blocks[1][1])
        self.assertIn("PASSED", blocks[1][1])
        data = tool["render_png"](blocks)
        lines = tool["_lines"](blocks)
        columns = max(len(text) for text, _heading in lines)
        width, height, foreground, heading = _decoded(data)
        self.assertEqual(width, tool["MARGIN"] * 2 + columns * tool["CELL_W"] * tool["SCALE"])
        self.assertEqual(height, tool["MARGIN"] * 2 + len(lines) * tool["CELL_H"] * tool["SCALE"])
        self.assertGreater(foreground, 100)
        self.assertGreater(heading, 20)

    def test_unknown_character_is_not_replaced(self):
        with self.assertRaises(ValueError):
            tool["render_png"]([("ok", "caf\u00e9")])


if __name__ == "__main__":
    unittest.main()
