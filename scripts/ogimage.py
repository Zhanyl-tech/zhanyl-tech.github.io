#!/usr/bin/env python3
"""
ogimage.py — branded social preview cards (1200x630)
====================================================

Every post gets an og:image. Without one, LinkedIn and X render your link as a
bare grey text row; with one, it renders as a card. This is the single highest
leverage thing for click-through, so it runs automatically in the publish flow.

Renders SVG -> PNG via rsvg-convert (already on this machine via librsvg).
No Python dependencies beyond the stdlib.

Usage:
    python3 scripts/ogimage.py --post content/blog/2026-07-26-my-post.md
    python3 scripts/ogimage.py --all
    python3 scripts/ogimage.py --default          # site-wide fallback card
"""

from __future__ import annotations

import argparse
import html
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OG_DIR = ROOT / "static" / "images" / "og"

WIDTH, HEIGHT = 1200, 630

# Matches the site palette in assets/css/extended/custom.css
BG = "#e7ebf8"
CARD = "#fcfcfb"
INK = "#111114"
INK_2 = "#57575c"
INK_3 = "#8e8e95"
RULE = "#e7e7eb"
ACCENT = "#1d4ed8"

SERIF = "Lora, Georgia, 'Times New Roman', serif"
SANS = "Inter, 'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', 'SF Mono', Menlo, monospace"

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


def render(svg: str, out_path: Path) -> None:
    binary = shutil.which("rsvg-convert")
    if not binary:
        raise SystemExit(
            "rsvg-convert not found. Install with:  brew install librsvg"
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [binary, "-w", str(WIDTH), "-h", str(HEIGHT), "-o", str(out_path), "-"],
        input=svg.encode("utf-8"),
        check=True,
    )


def card_for_post(post: Path) -> Path | None:
    meta = parse_frontmatter(post)
    title = meta.get("title")
    if not title:
        print(f"  skip (no title): {post}")
        return None

    section = post.parent.name
    kicker = SECTION_KICKER.get(section, section.upper())
    footer = meta.get("description", "ML Infrastructure · Quantitative Finance")
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
        svg = build_svg(
            "Building systems for models, markets, and scale.",
            "ML INFRASTRUCTURE · QUANTITATIVE FINANCE",
            "GPU clusters, inference systems, distributed training",
        )
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
        posts = sorted(
            p
            for p in (ROOT / "content").rglob("*.md")
            if p.name != "_index.md" and p.parent.name != "content"
        )

    for post in posts:
        out = card_for_post(post)
        if out:
            print(f"  wrote {out.relative_to(ROOT)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
