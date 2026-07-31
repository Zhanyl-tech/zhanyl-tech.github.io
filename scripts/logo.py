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
# needs 303/148 = 2.047x. Used by the stacked icon, where the two glyphs sit at
# equal weight. Re-derive with scripts/measure_glyphs.py if the typeface changes.
INFINITY_SCALE = 2.047

# ── Glyph metrics ───────────────────────────────────────────────────────────
#
# Ink bounds as fractions of font-size, measured from the text anchor with
# dominant-baseline="central". These are font metrics, so they hold at any size
# and let the lockup be *derived* rather than nudged into place by eye:
#
#          ink left   ink right   ink top   ink bottom   height
#   18       +0.100      +1.135    -0.745       +0.010    0.755
#   ∞        +0.020      +0.580    -0.495       -0.125    0.370
#
# Re-derive with scripts/measure_glyphs.py if the typeface ever changes.
M_DIGITS = {"left": 0.100, "right": 1.135, "top": -0.745, "bottom": 0.010, "h": 0.755}
M_INF = {"left": 0.020, "right": 0.580, "top": -0.495, "bottom": -0.125, "h": 0.370}

# The mark reads 18^∞ — eighteen to the infinite — so the ∞ is a true exponent:
# smaller than the digits and lifted to sit against their cap line, not a second
# character of equal weight parked alongside them.
#
# 0.58 is the ∞ ink height as a fraction of the digits' ink height, which is
# where typographic superscripts sit. Raise it toward 1.0 to flatten the mark
# back into two equal glyphs; drop it to make the exponent more delicate.
EXPONENT_RATIO = 0.58

# Font-size of the digits, in viewBox units. Everything else is derived from it.
DIGIT_FS = 88


def mark_svg(color: str, w: int = 210, h: int = 160, bg: str | None = None) -> str:
    """The horizontal 18^∞ lockup that sits beside the name.

    Both glyph positions are solved from M_DIGITS / M_INF rather than nudged by
    eye, because eyeballing this went wrong three separate ways: a gap opened
    when the glyphs were advanced by the digits' width (their side bearings
    differ), the ∞ was once "centred" onto the digits' midline and stopped
    reading as an exponent at all, and before that it was scaled by a factor
    guessed from the em box rather than the ink.

    Two constraints define the layout:

      horizontal   the ∞ ink starts exactly where the digits' ink ends, so the
                   two are flush with no visible space between them
      vertical     the ∞ ink top aligns with the digits' ink top, which is what
                   makes it sit as a power rather than as a second character

    The result is then centred on its true ink bounds, so the box's padding is
    even no matter what DIGIT_FS or EXPONENT_RATIO are set to.
    """
    d_fs = DIGIT_FS
    # Ink height ratio, converted to a font-size ratio via the two glyph heights.
    i_fs = d_fs * EXPONENT_RATIO * M_DIGITS["h"] / M_INF["h"]

    # Solve positions relative to an arbitrary origin, then translate to centre.
    d_x, d_y = 0.0, 0.0
    i_x = d_x + M_DIGITS["right"] * d_fs - M_INF["left"] * i_fs        # flush
    i_y = d_y + M_DIGITS["top"] * d_fs - M_INF["top"] * i_fs           # tops align

    ink_l = d_x + M_DIGITS["left"] * d_fs
    ink_r = i_x + M_INF["right"] * i_fs
    ink_t = d_y + M_DIGITS["top"] * d_fs
    ink_b = d_y + M_DIGITS["bottom"] * d_fs        # digits sit lowest

    dx = (w - (ink_r - ink_l)) / 2 - ink_l
    dy = (h - (ink_b - ink_t)) / 2 - ink_t

    plate = f'<rect width="{w}" height="{h}" rx="{h*0.2}" fill="{bg}"/>' if bg else ""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  {plate}
  <text x="{d_x + dx:.2f}" y="{d_y + dy:.2f}" dominant-baseline="central"
        font-family="{MONO}" font-size="{d_fs:.1f}" font-weight="500"
        fill="{color}">18</text>
  <text x="{i_x + dx:.2f}" y="{i_y + dy:.2f}" dominant-baseline="central"
        font-family="{MONO}" font-size="{i_fs:.1f}" font-weight="500"
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
