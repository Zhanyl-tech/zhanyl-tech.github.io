#!/usr/bin/env python3
"""
post_assets.py — the generated files a post actually publishes
===============================================================

vizpub.py writes more than a post uses into cope-drafts/vizpub/<slug>/: an
overview SVG, four slide SVGs, a slides page, a PDF when Chrome is present, the
Mermaid source and the diagram PNG. The post it writes references only the
PNG. weekly.sh used to copy that whole directory into static/, so files nobody
had been shown became public at /images/vizpub/, /images/slides/ and /slides/
the moment the pull request merged.

This lists only what the post uses. A file under the review directory counts
when the post names its site path (`/images/vizpub/<slug>.png`, or the same
path on an absolute URL), or when an HTML page or SVG that already counts
refers to it (the slides page brings in its slide images, and its PDF only if
it links one). weekly.sh copies that list and nothing else, and opens each
file for the reviewer before the slug confirmation. Everything else stays in
the gitignored review directory.

The directory mirrors static/, so each path printed is both the file's place
under the review directory and its place under static/.

    python3 scripts/post_assets.py content/experiments/<slug>.md
    python3 scripts/post_assets.py content/experiments/<slug>.md -0              # NUL-separated
    python3 scripts/post_assets.py content/experiments/<slug>.md --unreferenced  # what stays behind

Exit status: 0, also when there is no review directory (nothing to publish);
2 on a usage error. Standard library only.
"""

from __future__ import annotations

import argparse
import posixpath
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
REVIEW_ROOT = ROOT / "cope-drafts" / "vizpub"  # keep in step with scripts/vizpub.py

# Files whose own references are followed. Anything else (PNG, PDF, .mmd) is a
# leaf: it can be published, but it cannot pull in anything else.
_CONTAINERS = {".html", ".htm", ".svg"}
# src, href and xlink:href attribute values in HTML and SVG.
_ATTR_REF = re.compile(r"""(?:\bsrc|\bhref|xlink:href)\s*=\s*["']([^"']+)["']""", re.IGNORECASE)


def review_files(review_dir: Path) -> set[str]:
    """Every regular file under the review directory, as a POSIX relative path."""
    if not review_dir.is_dir():
        return set()
    return {p.relative_to(review_dir).as_posix() for p in review_dir.rglob("*") if p.is_file()}


def mentions(text: str, rel: str) -> bool:
    """True when `text` names the site path /<rel> as a whole path.

    The path has to start a URL (after whitespace, a quote, "(", "=", "[" or
    "<", or at a line start) or follow a scheme and host, and it has to end
    there too, so /images/vizpub/a.png does not match /x/images/vizpub/a.png
    or /images/vizpub/a.png.bak.
    """
    pattern = (
        r"(?:(?<=[\s\"'(=\[<])|^|https?://[^/\s\"'()<>]+)"
        + "/"
        + re.escape(rel)
        + r"(?=$|[\s\"'()<>#?\]])"
    )
    return re.search(pattern, text, re.MULTILINE) is not None


def resolve_ref(ref: str, from_rel: str) -> str | None:
    """Map a reference inside the asset at `from_rel` to a review-relative path.

    Root-relative references are site paths; relative ones resolve against the
    referring file's directory, which is also its directory under static/.
    References to another origin, fragments and data: URIs return None.
    """
    parts = urlsplit(ref.strip())
    if parts.scheme or parts.netloc:
        return None
    path = unquote(parts.path)
    if not path:
        return None
    if path.startswith("/"):
        rel = posixpath.normpath(path.lstrip("/"))
    else:
        rel = posixpath.normpath(posixpath.join(posixpath.dirname(from_rel), path))
    if rel.startswith("../") or rel in ("..", "."):
        return None
    return rel


def referenced(post_text: str, review_dir: Path) -> list[str]:
    """Review-relative paths of the files the post publishes, sorted."""
    files = review_files(review_dir)
    chosen = {rel for rel in files if mentions(post_text, rel)}
    queue = sorted(chosen)
    while queue:
        rel = queue.pop()
        if Path(rel).suffix.lower() not in _CONTAINERS:
            continue
        text = (review_dir / rel).read_text(encoding="utf-8", errors="replace")
        for ref in _ATTR_REF.findall(text):
            target = resolve_ref(ref, rel)
            if target in files and target not in chosen:
                chosen.add(target)
                queue.append(target)
    return sorted(chosen)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List the generated assets a post references.")
    parser.add_argument("post", type=Path, help="the post, e.g. content/experiments/<slug>.md")
    parser.add_argument(
        "--review-dir",
        type=Path,
        help="directory holding the post's generated files (default: cope-drafts/vizpub/<post stem>)",
    )
    parser.add_argument("-0", dest="nul", action="store_true", help="separate paths with NUL, not newline")
    parser.add_argument(
        "--unreferenced", action="store_true", help="list the files the post does NOT reference instead"
    )
    args = parser.parse_args(argv)

    if not args.post.is_file():
        print(f"error: no such post: {args.post}", file=sys.stderr)
        return 2
    review_dir = args.review_dir or (REVIEW_ROOT / args.post.stem)
    used = referenced(args.post.read_text(encoding="utf-8"), review_dir)
    out = sorted(review_files(review_dir) - set(used)) if args.unreferenced else used
    sep = "\0" if args.nul else "\n"
    sys.stdout.write("".join(rel + sep for rel in out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
