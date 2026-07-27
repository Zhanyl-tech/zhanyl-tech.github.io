#!/usr/bin/env python3
"""
logo.py — the ∞18 mark, plus the favicon set derived from it.

Optical sizing note: ∞ and 18 set at the same font-size do *not* look the same
size. ∞ sits around the x-height and is wide; digits run to cap-height and are
narrow. Matching them means scaling ∞ up and nudging its baseline, which is what
INFINITY_SCALE and INFINITY_DY below are for. Everything else here is plumbing.

    python3 scripts/logo.py                 # default colour
    python3 scripts/logo.py --color "#f5b544"
    python3 scripts/logo.py --variants      # contact sheet of colour options
"""

from __future__ import annotations

import argparse
import html
import shutil
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"

# Amber against the navy page: reads as ticker-board / trading-floor rather than
# as another framework blue, and it is the one hue on the page not already
# carrying meaning (blue = links, green = shell).
DEFAULT_COLOR = "#f5b544"

MONO = "'JetBrains Mono', 'SF Mono', Menlo, monospace"

# Measured, not guessed. At a common font-size the ∞ glyph's ink is 148px tall
# against 303px for "18" in JetBrains Mono, so matching their apparent size
# needs 303/148 = 2.047x. Re-derive with scripts/measure_glyphs.py if the
# typeface ever changes.
INFINITY_SCALE = 2.047
# Matching the ink *height* does not centre it. Rendered on a shared baseline
# with dominant-baseline="central", both glyphs come out 46.8 units tall — the
# scale above is exact — but the ∞ ink sits 16.5 units higher than the digits',
# because the two glyphs are placed differently inside their em boxes. Nudge it
# back down by that measured amount, as a fraction of the mark's height.
INFINITY_DY = 16.5 / 160


def mark_svg(color: str, w: int = 210, h: int = 160, bg: str | None = None) -> str:
    """The horizontal 18∞ lockup that sits beside the name.

    The box is deliberately taller than the visible ink. At the scale needed to
    match the digits, the ∞ em-box exceeds the box sized to those digits and the
    glyph is silently cropped — which is exactly what made the first attempts
    look wrong even with the correct scale factor.

    Both x positions are measured, not chosen. Rendered at a text x of 20:

        18   fs 62.0    ink 26.0 .. 90.5   (left side bearing 6.0)
        ∞    fs 126.9   ink 22.5 .. 93.5   (left side bearing 2.5)

    The two side bearings differ, so setting the glyphs flush is not a matter of
    advancing by the digits' width — do that and a 3.5px gap opens up. For
    digits at DIGIT_X the ∞ belongs at DIGIT_X + 68, which puts the start of its
    ink exactly where theirs ends. DIGIT_X is then chosen so the leftmost ink
    stays at 22.5, where it sat when the ∞ led, leaving the framing unchanged by
    the swap.
    """
    fs = 62
    cy = h / 2
    digit_x = 16.5
    inf_x = digit_x + 68
    plate = f'<rect width="{w}" height="{h}" rx="{h*0.2}" fill="{bg}"/>' if bg else ""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  {plate}
  <text x="{digit_x}" y="{cy}" dominant-baseline="central"
        font-family="{MONO}" font-size="{fs}" font-weight="500"
        fill="{color}">18</text>
  <text x="{inf_x}" y="{cy + h*INFINITY_DY}" dominant-baseline="central"
        font-family="{MONO}" font-size="{fs*INFINITY_SCALE:.1f}" font-weight="500"
        fill="{color}">∞</text>
</svg>"""


def icon_svg(color: str, size: int = 512, plate: str = "#141a23") -> str:
    """Square icon. Stacked, because 18∞ side by side is illegible at 32px.

    Reading order follows the lockup: 18 first, so the icon and the wordmark
    are not two different marks.
    """
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">
  <rect width="{size}" height="{size}" rx="{size*0.22}" fill="{plate}"/>
  <text x="{size/2}" y="{size*0.36}" text-anchor="middle" dominant-baseline="central"
        font-family="{MONO}" font-size="{size*0.34:.0f}" font-weight="500"
        fill="{color}">18</text>
  <text x="{size/2}" y="{size*0.66}" text-anchor="middle" dominant-baseline="central"
        font-family="{MONO}" font-size="{size*0.34*INFINITY_SCALE:.0f}" font-weight="500"
        fill="{color}">∞</text>
</svg>"""


def pinned_tab_svg() -> str:
    """Safari pinned tabs are a single-colour mask; no plate, no fills."""
    return """<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
  <text x="256" y="205" text-anchor="middle" dominant-baseline="central"
        font-family="'JetBrains Mono', monospace" font-size="356" font-weight="600"
        fill="black">∞</text>
  <text x="256" y="358" text-anchor="middle" dominant-baseline="central"
        font-family="'JetBrains Mono', monospace" font-size="174" font-weight="600"
        fill="black">18</text>
</svg>"""


def render(svg: str, out: Path, w: int, h: int | None = None) -> None:
    binary = shutil.which("rsvg-convert")
    if not binary:
        raise SystemExit("rsvg-convert not found. brew install librsvg")
    out.parent.mkdir(parents=True, exist_ok=True)
    args = [binary, "-w", str(w)]
    if h:
        args += ["-h", str(h)]
    subprocess.run(args + ["-o", str(out), "-"], input=svg.encode(), check=True)


def png_to_ico(pngs: list[Path], out: Path) -> None:
    entries = []
    for p in pngs:
        data = p.read_bytes()
        width, height = struct.unpack(">II", data[16:24])
        entries.append((0 if width >= 256 else width, 0 if height >= 256 else height, data))

    header = struct.pack("<HHH", 0, 1, len(entries))
    offset = 6 + 16 * len(entries)
    directory, blobs = b"", b""
    for width, height, data in entries:
        directory += struct.pack("<BBBBHHII", width, height, 0, 0, 1, 32, len(data), offset)
        blobs += data
        offset += len(data)
    out.write_bytes(header + directory + blobs)


def variants_sheet(colors: dict[str, str]) -> Path:
    """Contact sheet so a colour can be chosen without a rebuild each time."""
    cell_w, cell_h, pad = 300, 170, 26
    w = cell_w * 2 + pad * 2
    h = cell_h * ((len(colors) + 1) // 2) + pad * 2 + 44

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        f'<rect width="{w}" height="{h}" fill="#0f141b"/>',
        f'<text x="{pad}" y="{pad+18}" font-family={MONO!r} font-size="15" fill="#828c98">'
        f'MARK COLOUR OPTIONS</text>',
    ]
    for i, (name, col) in enumerate(colors.items()):
        x = pad + (i % 2) * cell_w
        y = pad + 40 + (i // 2) * cell_h
        parts.append(f'<g transform="translate({x},{y})">')
        parts.append(f'<rect width="{cell_w-18}" height="{cell_h-22}" rx="8" fill="#141a23" stroke="#262d38"/>')
        # Icon + lockup together, as they appear in the header.
        parts.append(f'<g transform="translate(16,18) scale(0.17)">{icon_svg(col)}</g>')
        parts.append(f'<g transform="translate(112,26) scale(0.62)">{mark_svg(col)}</g>')
        parts.append(
            f'<text x="16" y="{cell_h-40}" font-family={MONO!r} font-size="12" fill="#e9eff5">{html.escape(name)}</text>'
            f'<text x="16" y="{cell_h-24}" font-family={MONO!r} font-size="11" fill="#828c98">{col}</text>'
        )
        parts.append("</g>")
    parts.append("</svg>")

    svg = "\n".join(parts)
    out = ROOT / "static" / "images" / "logo-variants.png"
    render(svg, out, w * 2)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--color", default=DEFAULT_COLOR)
    ap.add_argument("--variants", action="store_true", help="render the colour sheet only")
    args = ap.parse_args()

    if args.variants:
        out = variants_sheet({
            "amber — ticker board":  "#f5b544",
            "violet — AI era":       "#a78bfa",
            "cyan — terminal":       "#22d3ee",
            "coral — signal":        "#fb7185",
            "lime — P&L green":      "#a3e635",
            "gold — solid":          "#eab308",
        })
        print(f"  wrote {out.relative_to(ROOT)}")
        return

    color = args.color
    images = STATIC / "images"

    # Header lockup, as SVG so it stays crisp at any scale.
    (images / "logo.svg").write_text(mark_svg(color), encoding="utf-8")
    print("  wrote static/images/logo.svg")

    for path, size in {
        STATIC / "favicon-16x16.png": 16,
        STATIC / "favicon-32x32.png": 32,
        STATIC / "apple-touch-icon.png": 180,
        images / "avatar.png": 400,
    }.items():
        render(icon_svg(color), path, size, size)
        print(f"  wrote {path.relative_to(ROOT)}")

    (STATIC / "safari-pinned-tab.svg").write_text(pinned_tab_svg(), encoding="utf-8")
    print("  wrote static/safari-pinned-tab.svg")

    png_to_ico([STATIC / "favicon-16x16.png", STATIC / "favicon-32x32.png"],
               STATIC / "favicon.ico")
    print("  wrote static/favicon.ico")


if __name__ == "__main__":
    main()
