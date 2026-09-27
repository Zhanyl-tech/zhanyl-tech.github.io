#!/usr/bin/env python3
"""
static_diagrams.py — animation-free twins of the animated diagrams
==================================================================

The diagrams in static/images/diagrams/ animate with SMIL (<animate>). SMIL
runs inside an <img> and ignores CSS, so neither prefers-reduced-motion nor a
pause control can reach it (WCAG 2.2.2, Pause, Stop, Hide). The fix is a still
twin, <name>.static.svg, which the image render hook
(layouts/_default/_markup/render-image.html) serves through
<source media="(prefers-reduced-motion: reduce)">.

A twin is the same file with every <animate>, <animateTransform> and
<animateMotion> element removed, so each animated attribute falls back to the
base value written on its element. That is only correct if the base value is a
sensible still frame; the diagrams here were checked by rendering the twins on
2026-09-26 (nothing disappears, nothing is left mid-sweep). Re-check by eye
after drawing a new diagram.

Usage:
    python3 scripts/static_diagrams.py            # (re)write every twin
    python3 scripts/static_diagrams.py --check    # exit 1 if any twin is stale

Standard library only, so it runs on any Python 3.9+.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIAGRAMS = ROOT / "static" / "images" / "diagrams"

# Self-closing and paired forms. The diagrams use only the first; the second is
# here so a hand-edited diagram cannot slip an animation through.
_SELF_CLOSING = re.compile(r"\s*<animate(?:Transform|Motion)?\b[^>]*/>")
_PAIRED = re.compile(
    r"\s*<animate(?:Transform|Motion)?\b[^>]*>.*?</animate(?:Transform|Motion)?>",
    re.DOTALL,
)


def still(svg: str) -> str:
    """Return the SVG with every SMIL animation element removed."""
    out = _PAIRED.sub("", _SELF_CLOSING.sub("", svg))
    if "<animate" in out:
        raise ValueError("an <animate…> element survived; unsupported form")
    return out


def sources() -> list[Path]:
    return sorted(p for p in DIAGRAMS.glob("*.svg") if not p.name.endswith(".static.svg"))


def twin(path: Path) -> Path:
    return path.with_name(path.stem + ".static.svg")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--check", action="store_true", help="fail if any twin is missing or stale")
    args = parser.parse_args(argv)

    stale = []
    for path in sources():
        expected = still(path.read_text(encoding="utf-8"))
        target = twin(path)
        current = target.read_text(encoding="utf-8") if target.exists() else None
        if current == expected:
            continue
        if args.check:
            stale.append(target.name)
        else:
            target.write_text(expected, encoding="utf-8")
            print(f"  wrote {target.relative_to(ROOT)}")
    if stale:
        print("stale or missing still twins: " + ", ".join(stale), file=sys.stderr)
        print("run: python3 scripts/static_diagrams.py", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
