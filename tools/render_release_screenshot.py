"""Draw a release PNG from a real failing run and a real passing run.

The command output is painted unchanged. Pillow and the vendored JetBrains Mono
(no ligatures) are used only for this image. ProofCLI itself has no runtime
dependencies. Elapsed time and the temporary directory come from the process
and are not rewritten. The PNG has no text or time metadata.
"""

import io
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = ROOT / "tools" / "fonts"
REGULAR = FONT_DIR / "JetBrainsMonoNL-Regular.ttf"
BOLD = FONT_DIR / "JetBrainsMonoNL-Bold.ttf"
ASSET_NAME = "proofcli-screenshot.png"
FAILING = "examples/export/wrong-value.json"
PASSING = "examples/export/good.json"

# Logical sizes are doubled so the file is a crisp 2x image.
SCALE = 2
BODY = 20 * SCALE
LABEL = 26 * SCALE
LINE = 32 * SCALE
PAD = 32 * SCALE
BAR = 8 * SCALE
GAP = 16 * SCALE
MIN_WIDTH = 640 * SCALE

BG = (18, 20, 16)
PANEL = (28, 31, 26)
FG = (236, 235, 227)
LIME = (213, 255, 63)
MUTED = (150, 153, 141)
FAIL = (255, 91, 59)
PASS_COLOR = (61, 220, 151)
RULE = (65, 68, 58)


def _require_text(text):
    for char in text:
        if char == "\n":
            continue
        if ord(char) < 32 or ord(char) > 126:
            raise ValueError(f"refusing to omit unsupported character {char!r} from the screenshot")


def _fonts():
    from PIL import ImageFont
    regular = ImageFont.truetype(str(REGULAR), BODY)
    label = ImageFont.truetype(str(BOLD), LABEL)
    return regular, label


def _width(font, text):
    if not text:
        return 0
    return int(font.getlength(text) + 0.999)


def render_png(blocks):
    """Return PNG bytes. `blocks` are (heading, stdout) from `capture`."""
    for heading, body in blocks:
        _require_text(heading)
        _require_text(body)
    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise RuntimeError("Pillow is required to draw the release screenshot") from exc
    regular, label = _fonts()
    sections = []
    content_width = 0
    for index, (heading, body) in enumerate(blocks):
        accent = FAIL if index == 0 else PASS_COLOR
        title = "FAILED" if index == 0 else "PASSED"
        content_width = max(content_width, _width(label, title))
        heading_lines = heading.splitlines() or [""]
        body_lines = body.splitlines() or [""]
        for line in heading_lines + body_lines:
            content_width = max(content_width, _width(regular, line))
        sections.append((accent, title, heading_lines, body_lines))
    width = max(MIN_WIDTH, content_width + PAD * 2 + BAR + PAD // 2)
    text_x = BAR + PAD
    rows = []
    y = PAD
    for accent, title, heading_lines, body_lines in sections:
        top = y
        rows.append(("text", text_x, y, title, label, accent))
        y += LABEL + GAP
        for number, line in enumerate(heading_lines):
            color = LIME if number == 0 else MUTED
            rows.append(("text", text_x, y, line, regular, color))
            y += LINE
        y += GAP // 2
        rows.append(("rule", text_x, y, width - PAD))
        y += GAP
        panel_top = y - GAP // 3
        panel_lines = body_lines
        panel_bottom = y + LINE * len(panel_lines) + GAP // 3
        rows.append(("panel", BAR, panel_top, width, panel_bottom, accent))
        for line in panel_lines:
            rows.append(("text", text_x, y, line, regular, FG))
            y += LINE
        y = panel_bottom + GAP
        rows.append(("bar", 0, top, BAR, y - GAP // 2, accent))
        y += GAP
    height = y
    image = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(image)
    # Panels and bars first, then text, so antialiased glyphs stay on top.
    for kind, *rest in rows:
        if kind == "panel":
            left, top, right, bottom, accent = rest
            draw.rectangle((left, top, right - 1, bottom - 1), fill=PANEL)
        elif kind == "bar":
            left, top, bar_w, bottom, accent = rest
            draw.rectangle((left, top, left + bar_w - 1, bottom - 1), fill=accent)
        elif kind == "rule":
            x0, rule_y, x1 = rest
            draw.rectangle((x0, rule_y, x1, rule_y + SCALE), fill=RULE)
    for kind, *rest in rows:
        if kind != "text":
            continue
        x, text_y, text, font, color = rest
        draw.text((x, text_y), text, font=font, fill=color, anchor="la")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", compress_level=9)
    return buffer.getvalue()


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
