#!/usr/bin/env python3
"""
linkcheck.py — check every internal link in a built Hugo site
=============================================================

Walks the HTML and XML files of a build directory (hugo -d DIR) and checks
that every internal reference resolves to a file in that directory:

  - <a href>, <link href>, <img src>, <script src>, <source src/srcset>,
    <iframe src>, <form action> when the target is on this site;
  - the URL-valued <meta> tags: og:url, og:image (and its :url and
    :secure_url forms) and twitter:image. A missing social card breaks no
    page, only every share of one, so nothing else would notice;
  - in every *.xml file (the RSS feeds, sitemap.xml): the text of <link>,
    <loc>, <guid> (unless isPermaLink="false") and <url>, and the href of
    <atom:link>/<xhtml:link>. A file that is not well-formed XML fails;
  - "#fragment" targets, on the same page or another one, against the id and
    name attributes of the target page;
  - absolute URLs on the site's own origin (--base-url) are treated as internal,
    because canonical, og:url, og:image and RSS links are written that way.

Not checked: links inside the escaped HTML of an RSS <description> (the same
links are checked on the page itself), JSON files such as the search index,
and anything reached only from CSS or JavaScript.

External URLs are counted and listed with --external, never fetched: a network
check belongs in a scheduled job, not in the build that gates a deploy.

Exit status: 0 when nothing is broken, 1 otherwise. Standard library only.

    python3 scripts/linkcheck.py public
    python3 scripts/linkcheck.py public --base-url https://zhanyl-tech.github.io/ --external
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

DEFAULT_BASE = "https://zhanyl-tech.github.io/"

# (tag, attribute) pairs that point at another resource.
LINK_ATTRS = {
    ("a", "href"),
    ("link", "href"),
    ("img", "src"),
    ("script", "src"),
    ("source", "src"),
    ("source", "srcset"),
    ("img", "srcset"),
    ("iframe", "src"),
    ("form", "action"),
}
# rel values on <link> that are not navigable resources on this site.
IGNORED_LINK_RELS = {"preconnect", "dns-prefetch"}
# <meta property|name=… content=URL> tags whose URL must exist on the site.
META_URL_KEYS = {
    "og:url",
    "og:image",
    "og:image:url",
    "og:image:secure_url",
    "twitter:image",
    "twitter:image:src",
}
# XML elements (local name, any namespace) whose text is a URL: RSS <link>,
# <guid> and <image><url>, sitemap <loc>. Atom and xhtml <link> carry it in
# href instead.
XML_TEXT_URLS = {"link", "loc", "guid", "url"}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.refs: list[tuple[str, str]] = []  # (tag, url)
        self.anchors: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: (v or "") for k, v in attrs}
        for key in ("id", "name"):
            if a.get(key):
                self.anchors.add(a[key])
        if tag == "link" and set(a.get("rel", "").split()) & IGNORED_LINK_RELS:
            return
        if tag == "meta":
            key = (a.get("property") or a.get("name") or "").strip().lower()
            if key in META_URL_KEYS and a.get("content", "").strip():
                self.refs.append((f"meta:{key}", a["content"].strip()))
            return
        for attr, value in a.items():
            if (tag, attr) not in LINK_ATTRS or not value:
                continue
            if attr == "srcset":
                for candidate in value.split(","):
                    url = candidate.strip().split(" ")[0]
                    if url:
                        self.refs.append((tag, url))
            else:
                self.refs.append((tag, value))


def xml_refs(path: Path) -> list[str]:
    """URLs named by an XML file's link-bearing elements; raises ET.ParseError."""
    refs: list[str] = []
    for el in ET.parse(path).iter():
        if not isinstance(el.tag, str):
            continue  # comments and processing instructions
        name = el.tag.rsplit("}", 1)[-1]
        if name == "link" and el.get("href"):
            refs.append(el.get("href", "").strip())
        elif name in XML_TEXT_URLS and len(el) == 0 and (el.text or "").strip():
            if name == "guid" and el.get("isPermaLink", "true").lower() == "false":
                continue
            refs.append((el.text or "").strip())
    return refs


def page_url(root: Path, html: Path, base: str) -> str:
    rel = html.relative_to(root).as_posix()
    if rel.endswith("index.html"):
        rel = rel[: -len("index.html")]
    return urljoin(base, rel)


def resolve(root: Path, base: str, url: str) -> Path | None:
    """Map an absolute on-site URL to the file that serves it, or None."""
    path = unquote(urlsplit(url).path)
    rel = path[len(urlsplit(base).path):] if path.startswith(urlsplit(base).path) else path.lstrip("/")
    target = root / rel
    if target.is_dir() or rel.endswith("/") or rel == "":
        target = target / "index.html"
    return target if target.is_file() else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check internal links in a built Hugo site.")
    parser.add_argument("root", type=Path, help="build directory (hugo -d ROOT)")
    parser.add_argument("--base-url", default=DEFAULT_BASE, help=f"site origin (default {DEFAULT_BASE})")
    parser.add_argument("--external", action="store_true", help="list external URLs (not fetched)")
    args = parser.parse_args(argv)

    root: Path = args.root.resolve()
    base = args.base_url if args.base_url.endswith("/") else args.base_url + "/"
    origin = "{0.scheme}://{0.netloc}".format(urlsplit(base))
    if not root.is_dir():
        print(f"error: no such directory: {root}", file=sys.stderr)
        return 2

    pages = sorted(root.rglob("*.html"))
    parsed: dict[Path, PageParser] = {}
    for html in pages:
        p = PageParser()
        p.feed(html.read_text(encoding="utf-8", errors="replace"))
        parsed[html] = p

    feeds = sorted(root.rglob("*.xml"))
    unparseable: list[str] = []
    sources: list[tuple[Path, list[str]]] = [
        (html, [raw for _tag, raw in p.refs]) for html, p in parsed.items()
    ]
    for xml in feeds:
        try:
            sources.append((xml, xml_refs(xml)))
        except ET.ParseError as exc:
            unparseable.append(f"{xml.relative_to(root).as_posix()}: {exc}")

    broken: dict[str, list[str]] = defaultdict(list)
    missing_fragments: dict[str, list[str]] = defaultdict(list)
    external: set[str] = set()
    checked = 0

    for html, refs in sources:
        here = page_url(root, html, base)
        for raw in refs:
            if raw.startswith(("mailto:", "tel:", "javascript:", "data:")):
                continue
            absolute = urljoin(here, raw)
            parts = urlsplit(absolute)
            if parts.scheme not in ("http", "https"):
                continue
            if f"{parts.scheme}://{parts.netloc}" != origin:
                external.add(absolute)
                continue
            checked += 1
            target = resolve(root, base, absolute)
            source = html.relative_to(root).as_posix()
            if target is None:
                broken[absolute].append(source)
                continue
            if parts.fragment and target.suffix == ".html":
                anchors = parsed.get(target).anchors if target in parsed else set()
                if unquote(parts.fragment) not in anchors:
                    missing_fragments[absolute].append(source)

    print(f"{len(pages)} HTML files, {len(feeds)} XML files, {checked} internal references checked, "
          f"{len(external)} distinct external URLs (not fetched)")
    for problem in unparseable:
        print(f"BAD-XML  {problem}")
    for url, sources in sorted(broken.items()):
        print(f"BROKEN   {url}")
        for s in sorted(set(sources))[:5]:
            print(f"           from {s}")
    for url, sources in sorted(missing_fragments.items()):
        print(f"NO-ANCHOR {url}")
        for s in sorted(set(sources))[:5]:
            print(f"           from {s}")
    if args.external:
        for url in sorted(external):
            print(f"external {url}")
    total = len(broken) + len(missing_fragments) + len(unparseable)
    print(f"{len(broken)} broken internal links, {len(missing_fragments)} missing fragment targets"
          + (f", {len(unparseable)} unparseable XML files" if unparseable else ""))
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
