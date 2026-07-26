#!/usr/bin/env python3
"""
favicons.py — generate the favicon set referenced by hugo.yaml.

hugo.yaml points at favicon.ico / favicon-16x16.png / favicon-32x32.png /
apple-touch-icon.png / safari-pinned-tab.svg, none of which existed, so every
page load produced 404s. This renders a simple monogram in the site palette.

Run once; re-run only if the mark changes.

Usage:  python3 scripts/favicons.py
"""

from __future__ import annotations

import shutil
import struct
import subprocess
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"

ACCENT = "#1d4ed8"
CARD = "#fcfcfb"

MONOGRAM = f"""<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
  <rect width="512" height="512" rx="112" fill="{ACCENT}"/>
  <text x="256" y="256" text-anchor="middle" dominant-baseline="central"
        font-family="Lora, Georgia, serif" font-size="300" font-weight="600"
        fill="{CARD}">Z</text>
</svg>"""

# Monochrome mask for Safari's pinned-tab rendering.
PINNED_TAB = """<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
  <text x="256" y="256" text-anchor="middle" dominant-baseline="central"
        font-family="Lora, Georgia, serif" font-size="380" font-weight="600"
        fill="black">Z</text>
</svg>"""


def render_png(svg: str, size: int, out: Path) -> None:
    binary = shutil.which("rsvg-convert")
    if not binary:
        raise SystemExit("rsvg-convert not found. Install with:  brew install librsvg")
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [binary, "-w", str(size), "-h", str(size), "-o", str(out), "-"],
        input=svg.encode("utf-8"),
        check=True,
    )


def png_to_ico(png_paths: list[Path], out: Path) -> None:
    """Pack PNGs into an .ico container (PNG-compressed entries, valid since Vista)."""
    entries = []
    for path in png_paths:
        data = path.read_bytes()
        width, height = struct.unpack(">II", data[16:24])
        entries.append((0 if width >= 256 else width, 0 if height >= 256 else height, data))

    header = struct.pack("<HHH", 0, 1, len(entries))
    offset = 6 + 16 * len(entries)
    directory, blobs = b"", b""
    for width, height, data in entries:
        directory += struct.pack(
            "<BBBBHHII", width, height, 0, 0, 1, 32, len(data), offset
        )
        blobs += data
        offset += len(data)
    out.write_bytes(header + directory + blobs)


def main() -> None:
    images = STATIC / "images"
    targets = {
        STATIC / "favicon-16x16.png": 16,
        STATIC / "favicon-32x32.png": 32,
        STATIC / "apple-touch-icon.png": 180,
        images / "avatar.png": 400,
    }
    for path, size in targets.items():
        render_png(MONOGRAM, size, path)
        print(f"  wrote {path.relative_to(ROOT)}")

    (STATIC / "safari-pinned-tab.svg").write_text(PINNED_TAB, encoding="utf-8")
    print("  wrote static/safari-pinned-tab.svg")

    # .ico bundles the 16px and 32px variants.
    png_to_ico(
        [STATIC / "favicon-16x16.png", STATIC / "favicon-32x32.png"],
        STATIC / "favicon.ico",
    )
    print("  wrote static/favicon.ico")


if __name__ == "__main__":
    main()
