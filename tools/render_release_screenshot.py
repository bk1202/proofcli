"""Draw a release PNG from a real failing run and a real passing run.

Runs the checked-in export examples with this checkout's ProofCLI and paints
their unmodified terminal text. The bitmap font and PNG writer use the standard
library only, so the release job does not install Node, Remotion, or Pillow.
Elapsed time and the temporary directory come from the process and are not
rewritten.
"""

import struct
import subprocess
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSET_NAME = "proofcli-screenshot.png"
FAILING = "examples/export/wrong-value.json"
PASSING = "examples/export/good.json"

# 5x7 glyphs, one row per string, '#' is ink. Printable ASCII only; anything
# else aborts so a character is never dropped or replaced.
_ROWS = {
    " ": [".....", ".....", ".....", ".....", ".....", ".....", "....."],
    "!": ["..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."],
    '"': [".#.#.", ".#.#.", ".....", ".....", ".....", ".....", "....."],
    "#": [".#.#.", ".#.#.", "#####", ".#.#.", "#####", ".#.#.", ".#.#."],
    "$": ["..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."],
    "%": ["##..#", "##.#.", "..#..", ".#...", "#.##.", "#..##", "....."],
    "&": [".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"],
    "'": ["..#..", "..#..", ".#...", ".....", ".....", ".....", "....."],
    "(": ["...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."],
    ")": [".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."],
    "*": [".....", "..#..", "#.#.#", ".###.", "#.#.#", "..#..", "....."],
    "+": [".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."],
    ",": [".....", ".....", ".....", ".....", "..#..", "..#..", ".#..."],
    "-": [".....", ".....", ".....", "#####", ".....", ".....", "....."],
    ".": [".....", ".....", ".....", ".....", ".....", ".##..", ".##.."],
    "/": ["....#", "...#.", "...#.", "..#..", ".#...", ".#...", "#...."],
    "0": [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "2": [".###.", "#...#", "....#", "..##.", ".#...", "#....", "#####"],
    "3": ["#####", "...#.", "..#..", "...#.", "....#", "#...#", ".###."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": ["..##.", ".#...", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##.."],
    ":": [".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."],
    ";": [".....", ".##..", ".##..", ".....", ".##..", "..#..", ".#..."],
    "<": ["...#.", "..#..", ".#...", "#....", ".#...", "..#..", "...#."],
    "=": [".....", ".....", "#####", ".....", "#####", ".....", "....."],
    ">": [".#...", "..#..", "...#.", "....#", "...#.", "..#..", ".#..."],
    "?": [".###.", "#...#", "....#", "..##.", "..#..", ".....", "..#.."],
    "@": [".###.", "#...#", "#.###", "#.#.#", "#.###", "#....", ".###."],
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "C": [".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."],
    "D": ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "G": [".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".###."],
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "I": [".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "J": ["..###", "...#.", "...#.", "...#.", "#..#.", "#..#.", ".##.."],
    "K": ["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"],
    "L": ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
    "M": ["#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"],
    "N": ["#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
    "Q": [".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "S": [".###.", "#...#", "#....", ".###.", "....#", "#...#", ".###."],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "U": ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "V": ["#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."],
    "W": ["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"],
    "X": ["#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"],
    "Y": ["#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."],
    "Z": ["#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"],
    "[": [".###.", ".#...", ".#...", ".#...", ".#...", ".#...", ".###."],
    "\\": ["#....", ".#...", ".#...", "..#..", "...#.", "...#.", "....#"],
    "]": [".###.", "...#.", "...#.", "...#.", "...#.", "...#.", ".###."],
    "^": ["..#..", ".#.#.", "#...#", ".....", ".....", ".....", "....."],
    "_": [".....", ".....", ".....", ".....", ".....", ".....", "#####"],
    "`": [".#...", "..#..", "...#.", ".....", ".....", ".....", "....."],
    "a": [".....", ".....", ".###.", "....#", ".####", "#...#", ".####"],
    "b": ["#....", "#....", "####.", "#...#", "#...#", "#...#", "####."],
    "c": [".....", ".....", ".###.", "#....", "#....", "#...#", ".###."],
    "d": ["....#", "....#", ".####", "#...#", "#...#", "#...#", ".####"],
    "e": [".....", ".....", ".###.", "#...#", "#####", "#....", ".###."],
    "f": ["..##.", ".#..#", ".#...", "###..", ".#...", ".#...", ".#..."],
    "g": [".....", ".....", ".####", "#...#", ".####", "....#", ".###."],
    "h": ["#....", "#....", "####.", "#...#", "#...#", "#...#", "#...#"],
    "i": ["..#..", ".....", ".##..", "..#..", "..#..", "..#..", ".###."],
    "j": ["...#.", ".....", "..##.", "...#.", "...#.", "#..#.", ".##.."],
    "k": ["#....", "#....", "#..#.", "#.#..", "##...", "#.#..", "#..#."],
    "l": [".##..", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "m": [".....", ".....", "##.#.", "#.#.#", "#.#.#", "#...#", "#...#"],
    "n": [".....", ".....", "####.", "#...#", "#...#", "#...#", "#...#"],
    "o": [".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###."],
    "p": [".....", ".....", "####.", "#...#", "####.", "#....", "#...."],
    "q": [".....", ".....", ".####", "#...#", ".####", "....#", "....#"],
    "r": [".....", ".....", "#.##.", "##..#", "#....", "#....", "#...."],
    "s": [".....", ".....", ".####", "#....", ".###.", "....#", "####."],
    "t": ["..#..", "..#..", "#####", "..#..", "..#..", "..#.#", "..##."],
    "u": [".....", ".....", "#...#", "#...#", "#...#", "#...#", ".####"],
    "v": [".....", ".....", "#...#", "#...#", "#...#", ".#.#.", "..#.."],
    "w": [".....", ".....", "#...#", "#...#", "#.#.#", "#.#.#", ".#.#."],
    "x": [".....", ".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#"],
    "y": [".....", ".....", "#...#", "#...#", ".####", "....#", ".###."],
    "z": [".....", ".....", "#####", "...#.", "..#..", ".#...", "#####"],
    "{": ["...##", "..#..", "..#..", ".#...", "..#..", "..#..", "...##"],
    "|": ["..#..", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "}": ["##...", "..#..", "..#..", "...#.", "..#..", "..#..", "##..."],
    "~": [".....", ".....", ".##.#", "#.##.", ".....", ".....", "....."],
}

CELL_W = 6
CELL_H = 9
SCALE = 3
MARGIN = 28
BG = (22, 23, 20)
FG = (236, 235, 227)
HEADING = (213, 255, 63)
RULE = (65, 68, 58)


def _glyph(char):
    rows = _ROWS.get(char)
    if rows is None:
        raise ValueError(f"refusing to omit unsupported character {char!r} from the screenshot")
    return rows


def _lines(blocks):
    """Return (text, is_heading) rows. Body text is the captured CLI output."""
    lines = []
    for index, (heading, body) in enumerate(blocks):
        if index:
            lines.append(("", False))
        for line in heading.splitlines() or [""]:
            lines.append((line, True))
        lines.append(("", False))
        for line in body.splitlines() or [""]:
            lines.append((line, False))
    return lines


def render_png(blocks):
    lines = _lines(blocks)
    columns = max((len(text) for text, _ in lines), default=1)
    width = MARGIN * 2 + columns * CELL_W * SCALE
    height = MARGIN * 2 + len(lines) * CELL_H * SCALE
    pixels = bytearray(bytes(BG) * (width * height))

    def paint(x, y, color):
        if 0 <= x < width and 0 <= y < height:
            start = (y * width + x) * 3
            pixels[start:start + 3] = bytes(color)

    for row, (text, heading) in enumerate(lines):
        color = HEADING if heading else FG
        origin_y = MARGIN + row * CELL_H * SCALE
        if text == "" and row not in (0, len(lines) - 1):
            # A blank separator between the command label and its output.
            rule_y = origin_y + (CELL_H * SCALE) // 2
            if heading is False and row > 0 and lines[row - 1][1] and row + 1 < len(lines) and not lines[row + 1][1]:
                for x in range(MARGIN, width - MARGIN):
                    paint(x, rule_y, RULE)
            continue
        for column, char in enumerate(text):
            origin_x = MARGIN + column * CELL_W * SCALE
            for gy, bits in enumerate(_glyph(char)):
                for gx, bit in enumerate(bits):
                    if bit != "#":
                        continue
                    for sy in range(SCALE):
                        for sx in range(SCALE):
                            paint(origin_x + gx * SCALE + sx, origin_y + gy * SCALE + sy, color)
    return _encode(width, height, pixels)


def _encode(width, height, pixels):
    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)
        raw.extend(pixels[y * stride:(y + 1) * stride])
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b"")


def run_spec(spec):
    completed = subprocess.run(
        [sys.executable, "-m", "proofcli", "run", spec],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if completed.stderr:
        raise RuntimeError(f"{spec} wrote stderr, which this screenshot does not expect:\n{completed.stderr}")
    return completed.returncode, completed.stdout


def capture():
    """Run both examples. Fail closed if they do not actually fail and pass."""
    fail_code, fail_out = run_spec(FAILING)
    pass_code, pass_out = run_spec(PASSING)
    if fail_code != 1 or "FAILED" not in fail_out or "999.00" not in fail_out:
        raise RuntimeError(f"failing example did not produce the real mismatch (exit {fail_code})")
    if pass_code != 0 or "PASSED" not in pass_out or "All 9 checks passed." not in pass_out:
        raise RuntimeError(f"passing example did not pass (exit {pass_code})")
    fail_heading = f"python -m proofcli run {FAILING}\nprocess exit: {fail_code}"
    pass_heading = f"python -m proofcli run {PASSING}\nprocess exit: {pass_code}"
    return [(fail_heading, fail_out), (pass_heading, pass_out)]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    destination = Path(argv[0]) if argv else ROOT / "dist" / ASSET_NAME
    blocks = capture()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(render_png(blocks))
    print(destination)


if __name__ == "__main__":
    main()
