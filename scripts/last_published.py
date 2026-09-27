#!/usr/bin/env python3
"""
last_published.py — the date of the newest published post, from the content
============================================================================

The weekly-drop workflow reports "N days since the last post". It used to take
the date of the last git commit touching content/blog, content/experiments or
content/notes, so any edit to an old post (a typo fix, a style change) reset
the clock: on 2026-09-26 it reported 48 days when the newest post was 62 days
old. And an empty `git log` fell through to epoch 0.

This reads the front matter instead: the newest `date:` among files in those
sections that are not `draft: true`, ignoring `_index.md`. It prints an ISO
date, or nothing when there is no published post, and `--days` prints the
whole days since that date (UTC), or `unknown`.

    python3 scripts/last_published.py            # 2026-07-26
    python3 scripts/last_published.py --days     # 62

Standard library only.
"""

from __future__ import annotations

import argparse
import re
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECTIONS = ("blog", "experiments", "notes")
_DATE = re.compile(r"^date:\s*[\"']?(\d{4}-\d{2}-\d{2})", re.MULTILINE)
_DRAFT = re.compile(r"^draft:\s*true\b", re.MULTILINE | re.IGNORECASE)


def _front_matter(text: str) -> str:
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    return text[3:end] if end != -1 else ""


def last_published(content: Path) -> date | None:
    newest: date | None = None
    for section in SECTIONS:
        for md in (content / section).glob("*.md"):
            if md.name == "_index.md":
                continue
            fm = _front_matter(md.read_text(encoding="utf-8"))
            if not fm or _DRAFT.search(fm):
                continue
            m = _DATE.search(fm)
            if not m:
                continue
            d = date.fromisoformat(m.group(1))
            if newest is None or d > newest:
                newest = d
    return newest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Newest published post date.")
    parser.add_argument("--days", action="store_true", help="print days since, or 'unknown'")
    parser.add_argument("--content", type=Path, default=ROOT / "content")
    parser.add_argument("--today", help="override today's date (YYYY-MM-DD), for tests")
    args = parser.parse_args(argv)

    newest = last_published(args.content)
    if not args.days:
        print(newest.isoformat() if newest else "")
        return 0
    today = date.fromisoformat(args.today) if args.today else datetime.now(timezone.utc).date()
    print((today - newest).days if newest else "unknown")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
