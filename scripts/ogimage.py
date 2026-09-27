#!/usr/bin/env python3
"""
ogimage.py — branded social preview cards (1200x630)
====================================================

Every post gets an og:image. Without one, LinkedIn and X render your link as a
bare grey text row; with one, it renders as a card. This is the single highest
leverage thing for click-through, so it runs automatically in the publish flow.

Renders SVG -> PNG with rsvg-convert (librsvg) when it is on PATH. Where it is
not, it falls back to resvg via the `resvg-py` package, reading fonts only from
OG_FONT_DIR (for example the OFL Instrument Serif, Inter and JetBrains Mono
files from github.com/google/fonts), so a card never silently picks up whatever
system font happens to be installed. After rendering, if Pillow is importable,
the PNG is re-saved losslessly with maximum zlib compression; the pixels are
identical.

The core stays standard library only; resvg-py and Pillow are optional.

Usage:
    python3 scripts/ogimage.py --post content/blog/2026-07-26-my-post.md
    python3 scripts/ogimage.py --all              # every published page
    python3 scripts/ogimage.py --default          # site-wide fallback card
"""

from __future__ import annotations

import argparse
import html
import io
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OG_DIR = ROOT / "static" / "images" / "og"

WIDTH, HEIGHT = 1200, 630

# Matches the site palette in assets/css/extended/custom.css
BG = "#0f141b"
CARD = "#161d27"
INK = "#e6edf3"
INK_2 = "#a8b3bf"
INK_3 = "#7d8590"
RULE = "#262d38"
ACCENT = "#58a6ff"

SERIF = "Instrument Serif, Lora, Georgia, 'Times New Roman', serif"
SANS = "Inter, 'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', 'SF Mono', Menlo, monospace"

# The site-wide fallback card (--default), served for every page without a
# card of its own. Its words also feed the og:image:alt of those pages
# (hugo.yaml params.defaultCardAlt, read by
# layouts/partials/templates/twitter_cards.html), because alt text has to
# describe the image, not the page; scripts/tests/test_scripts.py keeps the two
# in step. Until September 2026 the title ended in the single word "measured",
# which the fleet-health tools, tested only on simulators and synthetic trees,
# did not back.
DEFAULT_CARD_TITLE = "GPU scheduling and fleet health: what was measured, and on what."
DEFAULT_CARD_KICKER = "GPU CLUSTERS · SLURM & KUBERNETES"
DEFAULT_CARD_FOOTER = "Scheduler evaluation · GPU fleet health · measured vs asserted"

SECTION_KICKER = {
    "blog": "DEEP DIVE",
    "experiments": "LAB NOTE",
    "notes": "NOTE",
    "projects": "PROJECT",
}


def parse_frontmatter(path: Path) -> dict[str, str]:
    """Minimal YAML frontmatter reader — only the scalar keys we need."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    out: dict[str, str] = {}
    for line in text[3:end].splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip().strip('"').strip("'")
        if value:
            out[key.strip()] = value
    return out


def wrap(text: str, max_chars: int, max_lines: int) -> list[str]:
    """Greedy word wrap with an ellipsis on overflow."""
    words, lines, current = text.split(), [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
        if len(lines) == max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) == max_lines and len(" ".join(lines)) < len(text):
        lines[-1] = lines[-1].rstrip(",.;:") + "…"
    return lines


def build_svg(title: str, kicker: str, footer: str) -> str:
    # Long titles get a smaller face so they still fit the card.
    if len(title) <= 48:
        size, leading, max_chars = 68, 84, 26
    elif len(title) <= 90:
        size, leading, max_chars = 56, 70, 32
    else:
        size, leading, max_chars = 46, 58, 40

    lines = wrap(title, max_chars=max_chars, max_lines=4)
    block_height = len(lines) * leading
    start_y = 300 - block_height / 2 + leading * 0.75

    tspans = "".join(
        f'<tspan x="88" y="{start_y + i * leading:.0f}">{html.escape(line)}</tspan>'
        for i, line in enumerate(lines)
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">
  <rect width="{WIDTH}" height="{HEIGHT}" fill="{BG}"/>
  <rect x="40" y="40" width="{WIDTH - 80}" height="{HEIGHT - 80}" rx="18" fill="{CARD}"/>
  <rect x="40" y="40" width="8" height="{HEIGHT - 80}" rx="4" fill="{ACCENT}"/>

  <text x="88" y="150" font-family="{MONO}" font-size="21" font-weight="500"
        letter-spacing="2.6" fill="{INK_3}">{html.escape(kicker)}</text>

  <text font-family="{SERIF}" font-size="{size}" font-weight="600"
        fill="{INK}" letter-spacing="-0.6">{tspans}</text>

  <line x1="88" y1="486" x2="{WIDTH - 88}" y2="486" stroke="{RULE}" stroke-width="1.5"/>

  <text x="88" y="536" font-family="{SANS}" font-size="26" font-weight="600"
        fill="{INK}">Zhanyl Abdybaeva</text>
  <text x="88" y="568" font-family="{SANS}" font-size="20" fill="{INK_2}">{html.escape(footer)}</text>

  <text x="{WIDTH - 88}" y="553" text-anchor="end" font-family="{MONO}" font-size="19"
        fill="{INK_3}">zhanyl-tech.github.io</text>
</svg>"""


def _render_png(svg: str) -> bytes:
    binary = shutil.which("rsvg-convert")
    if binary:
        return subprocess.run(
            [binary, "-w", str(WIDTH), "-h", str(HEIGHT), "-"],
            input=svg.encode("utf-8"),
            check=True,
            capture_output=True,
        ).stdout
    try:
        import resvg_py  # type: ignore[import-not-found]
    except ImportError:
        raise SystemExit(
            "No renderer: install librsvg (brew install librsvg) for rsvg-convert,\n"
            "or `pip install resvg-py` and set OG_FONT_DIR to a directory of .ttf files."
        ) from None
    font_dir = os.environ.get("OG_FONT_DIR")
    if not font_dir or not Path(font_dir).is_dir():
        raise SystemExit("resvg-py needs OG_FONT_DIR: a directory holding the card fonts (.ttf)")
    return bytes(
        resvg_py.svg_to_bytes(
            svg_string=svg,
            width=WIDTH,
            height=HEIGHT,
            skip_system_fonts=True,
            font_dirs=[font_dir],
            serif_family="Instrument Serif",
            sans_serif_family="Inter",
            monospace_family="JetBrains Mono",
        )
    )


def _optimise(png: bytes) -> bytes:
    """Lossless re-encode (same pixels, smaller file) when Pillow is present.

    A card is a flat design with anti-aliased text: about a hundred distinct
    colours and an opaque background. When it has at most 256 colours and no
    transparency it is stored as a palette PNG, which is exact, not an
    approximation: the result is decoded again and compared pixel for pixel,
    and discarded if anything differs. On 2026-09-26 that halved the cards
    (default.png 33,934 -> 16,740 bytes) with zero pixel difference.
    """
    try:
        from PIL import Image, ImageChops  # type: ignore[import-not-found]
    except ImportError:
        return png
    image = Image.open(io.BytesIO(png))
    image.load()
    rgb = image.convert("RGB")
    opaque = image.mode != "RGBA" or image.getchannel("A").getextrema() == (255, 255)
    candidates = []
    if opaque and rgb.getcolors(256) is not None:
        paletted = rgb.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        candidates.append(paletted)
    candidates.append(image)
    best = png
    for candidate in candidates:
        out = io.BytesIO()
        candidate.save(out, format="PNG", optimize=True, compress_level=9)
        data = out.getvalue()
        decoded = Image.open(io.BytesIO(data)).convert("RGBA")
        if ImageChops.difference(decoded, image.convert("RGBA")).getbbox() is not None:
            continue
        if len(data) < len(best):
            best = data
    return best


def render(svg: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(_optimise(_render_png(svg)))


def card_for_post(post: Path) -> Path | None:
    meta = parse_frontmatter(post)
    title = meta.get("title")
    if not title:
        print(f"  skip (no title): {post}")
        return None

    section = post.parent.name
    kicker = SECTION_KICKER.get(section, section.upper())
    footer = meta.get("description", "GPU scheduling · Slurm & Kubernetes · fleet health")
    footer = wrap(footer, max_chars=62, max_lines=1)[0] if footer else ""

    out_path = OG_DIR / f"{post.stem}.png"
    render(build_svg(title, kicker, footer), out_path)
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate social preview cards.")
    parser.add_argument("--post", help="Path to a single markdown post")
    parser.add_argument("--all", action="store_true", help="Every post in content/")
    parser.add_argument("--default", action="store_true", help="Site-wide fallback card")
    args = parser.parse_args()

    if not any([args.post, args.all, args.default]):
        parser.error("pass one of --post, --all, or --default")

    if args.default:
        # Matches the homepage headline. An earlier card still advertised
        # "distributed training", a project that was retired.
        svg = build_svg(DEFAULT_CARD_TITLE, DEFAULT_CARD_KICKER, DEFAULT_CARD_FOOTER)
        out = OG_DIR / "default.png"
        render(svg, out)
        print(f"  wrote {out.relative_to(ROOT)}")

    posts: list[Path] = []
    if args.post:
        candidate = Path(args.post)
        if not candidate.is_absolute():
            candidate = ROOT / candidate
        if not candidate.exists():
            print(f"error: no such post: {args.post}", file=sys.stderr)
            return 1
        posts = [candidate]
    elif args.all:
        # Drafts are skipped: a card for an unpublished page is still served
        # from static/, which is how retired drafts ended up with public cards.
        posts = sorted(
            p
            for p in (ROOT / "content").rglob("*.md")
            if p.name != "_index.md"
            and p.parent.name != "content"
            and parse_frontmatter(p).get("draft", "").split("#")[0].strip().lower() != "true"
        )

    for post in posts:
        out = card_for_post(post)
        if out:
            print(f"  wrote {out.relative_to(ROOT)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
