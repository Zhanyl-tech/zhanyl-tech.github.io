"""Tests for the publishing scripts.

These scripts decide what is published under the site owner's name, so the
behaviours that protect that are pinned here: front matter that cannot break
the build, slugs that cannot escape their directory, generated SVG with its
script vectors removed, the review gate, the withdrawn-wording and
branch-reference rules, the cadence count, the link checker the deploy depends
on (pages, social-card meta tags, feeds), which generated assets a post
publishes, slide pages that link where the post really is, well-formed SVG,
and imports that work on the Python 3.9 macOS ships as python3.

Standard library only (unittest), so CI runs them with the runner's python3
and no install step:

    python3 -m unittest discover -s scripts/tests -v
"""

from __future__ import annotations

import ast
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import check_content  # noqa: E402
import last_published  # noqa: E402
import linkcheck  # noqa: E402
import ogimage  # noqa: E402
import post_assets  # noqa: E402
import social  # noqa: E402
import static_diagrams  # noqa: E402
import vizpub  # noqa: E402


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class VizpubFrontMatter(unittest.TestCase):
    """The old f-string front matter broke the whole Hugo build on a quote."""

    def test_awkward_titles_stay_one_scalar(self) -> None:
        payload = {
            "title": 'Why "paged" attention: beats contiguous KV',
            "description": "- leading dash, a colon: and a # hash",
            "tags": ["kv-cache", 'with "quotes"'],
        }
        fm = vizpub.build_frontmatter(payload, "2026-09-26", "true")
        lines = fm.splitlines()
        self.assertEqual(lines[0], "---")
        self.assertEqual(lines[-1], "---")
        values = dict(line.split(": ", 1) for line in lines[1:-1])
        # JSON strings are valid YAML scalars, so json.loads is a strict check.
        self.assertEqual(json.loads(values["title"]), payload["title"])
        self.assertEqual(json.loads(values["description"]), payload["description"])
        self.assertEqual(json.loads(values["tags"]), payload["tags"])
        self.assertEqual(values["draft"], "true")

    def test_generated_posts_are_always_drafts(self) -> None:
        fm = vizpub.build_frontmatter({"title": "t", "description": "d", "tags": []}, "2026-09-26", "false")
        self.assertIn("draft: true", fm)


class VizpubPaths(unittest.TestCase):
    def test_traversal_slug_is_flattened(self) -> None:
        slug = vizpub.safe_slug("../../layouts/partials/extend_head")
        self.assertRegex(slug, r"^[a-z0-9-]+$")
        self.assertNotIn("/", slug)
        self.assertNotIn(".", slug)

    def test_falls_back_to_the_next_candidate(self) -> None:
        self.assertEqual(vizpub.safe_slug("", "////", "Paged KV cache"), "paged-kv-cache")

    def test_no_usable_candidate_raises(self) -> None:
        with self.assertRaises(ValueError):
            vizpub.safe_slug("", "!!!", "///")

    def test_inside_refuses_escape(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "root"
            root.mkdir()
            self.assertEqual(vizpub.inside(root / "a.svg", root), (root / "a.svg").resolve())
            with self.assertRaises(ValueError):
                vizpub.inside(root / ".." / "escape.svg", root)


class VizpubSvgSanitising(unittest.TestCase):
    def test_script_vectors_removed(self) -> None:
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)">'
            "<script>alert(2)</script>"
            '<foreignObject><div>x</div></foreignObject>'
            '<a href="https://evil.example/">x</a>'
            '<use xlink:href="#ok"/>'
            '<rect onclick="steal()" width="1" height="1"/>'
            "</svg>"
        )
        out = vizpub.sanitize_svg(svg)
        for bad in ("<script", "foreignObject", "onload", "onclick", "evil.example"):
            self.assertNotIn(bad, out)
        self.assertIn('xlink:href="#ok"', out)
        self.assertIn('<rect width="1" height="1"/>', out)

    def test_model_id_is_current(self) -> None:
        self.assertEqual(vizpub.MODEL, "claude-opus-5")
        self.assertEqual(social.MODEL, "claude-opus-5")


class OgImageWrap(unittest.TestCase):
    def test_fits_without_ellipsis(self) -> None:
        self.assertEqual(ogimage.wrap("one two three", 20, 2), ["one two three"])

    def test_overflow_at_max_lines_gets_an_ellipsis(self) -> None:
        lines = ogimage.wrap("alpha beta gamma delta epsilon zeta eta theta", 11, 2)
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[-1].endswith("…"))


class SocialExtraction(unittest.TestCase):
    def test_tweets_fit_and_no_placeholder(self) -> None:
        body = ("A sentence with no numbers at all, repeated to be long. " * 20).strip()
        drafts = social.generate_by_extraction(
            {"title": "T", "description": "", "tags": "[slurm]"}, body, "https://example.org/x/"
        )
        for tweet in drafts["x"]["tweets"]:
            self.assertLessEqual(len(tweet), 275)
            self.assertNotIn("[", tweet)
        self.assertEqual(social.extract_signals(body)["numeric"], [])


class CheckContent(unittest.TestCase):
    def test_marker_blocks_a_published_post_but_not_a_draft(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            content = Path(d) / "content"
            marker = check_content.REVIEW_MARKER
            write(content / "blog" / "a.md", f"---\ntitle: a\ndraft: false\n---\n<!-- {marker} -->\n")
            write(content / "blog" / "b.md", f"---\ntitle: b\ndraft: true\n---\n<!-- {marker} -->\n")
            problems = check_content.check(content)
            self.assertEqual(len(problems), 1)
            self.assertIn("blog/a.md", problems[0])

    def test_project_needs_a_known_stage(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            content = Path(d) / "content"
            write(content / "projects" / "ok.md", '---\ntitle: ok\nstatus: "x"\nstage: "built"\n---\n')
            write(content / "projects" / "bad.md", '---\ntitle: bad\nstatus: "x"\nstage: "shipped"\n---\n')
            write(content / "projects" / "old.md", "---\ntitle: old\ndraft: true  # retired\n---\n")
            problems = check_content.check(content)
            self.assertEqual(len(problems), 1)
            self.assertIn("bad.md", problems[0])

    def test_marker_matches_vizpub(self) -> None:
        self.assertEqual(check_content.REVIEW_MARKER, vizpub.REVIEW_MARKER)
        weekly = (SCRIPTS / "weekly.sh").read_text(encoding="utf-8")
        self.assertIn(f'REVIEW_MARKER="{vizpub.REVIEW_MARKER}"', weekly)


class CheckContentBranchesAndWithdrawn(unittest.TestCase):
    def test_branch_named_outside_a_comment_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            content = Path(d) / "content"
            write(content / "experiments" / "a.md",
                  "---\ntitle: a\n---\nThe rows ran on the `improve/2026-09` branch.\n")
            write(content / "experiments" / "b.md",
                  "---\ntitle: b\n---\nPinned to `c02b52f`.\n<!-- OWNER: merge improve/2026-09\nfirst. -->\n")
            problems = check_content.check(content)
            self.assertEqual(len(problems), 1)
            self.assertIn("a.md", problems[0])
            self.assertIn("improve/2026-09", problems[0])

    # One sample of each withdrawn wording, in the file where it was published.
    SAMPLES = (
        ("content/projects/slinky-gitops.md",
         '"The kubelet does not have to\nmaintain a watch on each Secret mounted as a volume"'),
        ("static/images/figures/lserve-fig2-decode.svg",
         "<text>INT4 KV quantization reduces bytes per page read</text>"),
        ("static/images/diagrams/slinky-auth-rotation.svg", "<text>keeps serving the node's</text>"),
        ("hugo.yaml", "fact: 'a shared HCA is never attributed to a job.'"),
        ("content/about.md", "and refuse when a device is\nshared)."),
        ("layouts/index.html", "<p>A failed <code>nvidia-smi</code> query exits 0 instead of draining</p>"),
        ("static/images/architecture.svg", "<text>drain on persistent GPU faults, never on a failed query</text>"),
        ("static/images/diagrams/gpu-reaper-escalation.svg", "<text>Slurm sees allocations, not GPUs.</text>"),
        ("hugo.yaml", 'note: "Slurm model built · Kubernetes K0 + degenerate baselines measured"'),
        ("static/images/architecture.svg", "<text>dependency graph + read-only guard + MCP server built</text>"),
        ("scripts/ogimage.py", 'build_svg("Scheduling and fleet health for GPU clusters, measured.")'),
        ("content/now.md", "temporal separation and embargoes is doing real work in the evaluation harness"),
    )

    def test_each_withdrawn_wording_is_caught(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for rel, text in self.SAMPLES:
                path = root / rel
                old = path.read_text(encoding="utf-8") if path.exists() else "---\ntitle: x\n---\n"
                write(path, old + text + "\n")
            problems = check_content.check_withdrawn(root)
            joined = "\n".join(problems)
            for pattern, _globs, why in check_content.WITHDRAWN:
                self.assertIn(why, joined, f"no sample caught {pattern!r}")

    def test_corrected_wording_comments_drafts_and_corrections_pass(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write(root / "content" / "about.md",
                  "---\ntitle: About\n---\nnever for a failed query that carries\nno fault evidence, "
                  "and refuse when it can see that a port is shared.\n"
                  "<!-- OWNER: it used to say \"refuse when a device is shared\" -->\n")
            write(root / "content" / "projects" / "old.md",
                  "---\ntitle: old\ndraft: true\n---\na shared HCA is never attributed\n")
            write(root / "content" / "corrections.md",
                  "---\ntitle: Corrections\n---\nIt said it \"refuses to attribute a shared device\".\n")
            write(root / "static" / "images" / "architecture.svg",
                  "<svg><text>drain on persistent GPU faults, never on a query without fault evidence</text></svg>")
            write(root / "hugo.yaml", 'note: "K0 + three degenerate baselines measured once"\n')
            self.assertEqual(check_content.check_withdrawn(root), [])

    def test_the_site_passes(self) -> None:
        self.assertEqual(check_content.check(), [])
        self.assertEqual(check_content.check_withdrawn(), [])


class LastPublished(unittest.TestCase):
    def test_uses_front_matter_not_edits(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            content = Path(d)
            write(content / "blog" / "old.md", "---\ndate: 2026-07-26\ndraft: false\n---\nedited today\n")
            write(content / "blog" / "newer-draft.md", "---\ndate: 2026-09-20\ndraft: true\n---\n")
            write(content / "blog" / "_index.md", "---\ndate: 2026-09-25\n---\n")
            self.assertEqual(str(last_published.last_published(content)), "2026-07-26")

    def test_no_posts_is_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            out = subprocess.run(
                [sys.executable, str(SCRIPTS / "last_published.py"), "--days", "--content", d],
                capture_output=True, text=True, check=True,
            ).stdout.strip()
            self.assertEqual(out, "unknown")

    def test_days(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            write(Path(d) / "experiments" / "p.md", "---\ndate: 2026-07-26\n---\n")
            out = subprocess.run(
                [sys.executable, str(SCRIPTS / "last_published.py"), "--days", "--content", d,
                 "--today", "2026-09-26"],
                capture_output=True, text=True, check=True,
            ).stdout.strip()
            self.assertEqual(out, "62")


class LinkCheck(unittest.TestCase):
    def build(self, root: Path) -> None:
        write(root / "index.html", '<a href="/ok/">ok</a><a href="/ok/#here">frag</a>'
              '<a href="https://zhanyl-tech.github.io/ok/">abs</a><a href="https://example.org/">ext</a>')
        write(root / "ok" / "index.html", '<h2 id="here">x</h2><img src="/img.svg">')
        write(root / "img.svg", "<svg/>")

    def test_clean_site_passes(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            self.build(Path(d))
            self.assertEqual(linkcheck.main([d]), 0)

    def test_broken_link_and_missing_fragment_fail(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.build(root)
            write(root / "bad" / "index.html", '<a href="/draft-page/">x</a><a href="/ok/#nope">y</a>')
            self.assertEqual(linkcheck.main([d]), 1)

    def test_social_card_meta_tags_are_checked(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.build(root)
            write(root / "images" / "og" / "card.png", "png")
            good = ('<meta property="og:url" content="https://zhanyl-tech.github.io/ok/">'
                    '<meta property="og:image" content="https://zhanyl-tech.github.io/images/og/card.png">'
                    '<meta name="twitter:image" content="https://zhanyl-tech.github.io/images/og/card.png">'
                    '<meta property="og:image:alt" content="not a URL, not checked">')
            write(root / "p" / "index.html", good)
            self.assertEqual(linkcheck.main([d]), 0)
            for bad in ('<meta property="og:url" content="https://zhanyl-tech.github.io/gone/">',
                        '<meta property="og:image" content="https://zhanyl-tech.github.io/images/og/missing.png">',
                        '<meta name="twitter:image" content="/images/og/missing.png">'):
                write(root / "p" / "index.html", good + bad)
                self.assertEqual(linkcheck.main([d]), 1, bad)

    def test_feed_and_sitemap_links_are_checked(self) -> None:
        rss = ('<?xml version="1.0"?><rss xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
               '<link>https://zhanyl-tech.github.io/</link>'
               '<atom:link href="https://zhanyl-tech.github.io/index.xml" rel="self"/>'
               '<item><link>https://zhanyl-tech.github.io/ok/</link>'
               '<guid isPermaLink="false">tag:not-a-url</guid></item>{extra}</channel></rss>')
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.build(root)
            write(root / "index.xml", rss.format(extra=""))
            write(root / "sitemap.xml",
                  '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                  '<url><loc>https://zhanyl-tech.github.io/ok/</loc></url></urlset>')
            self.assertEqual(linkcheck.main([d]), 0)
            write(root / "index.xml", rss.format(extra="<item><link>https://zhanyl-tech.github.io/gone2/</link></item>"))
            self.assertEqual(linkcheck.main([d]), 1)
            write(root / "index.xml", rss.format(extra=""))
            write(root / "sitemap.xml", "<urlset><url><loc>https://zhanyl-tech.github.io/gone3/</loc></url></urlset>")
            self.assertEqual(linkcheck.main([d]), 1)
            write(root / "sitemap.xml", "<urlset><url><loc>unclosed")
            self.assertEqual(linkcheck.main([d]), 1)


def vizpub_tree(review: Path, slug: str, section: str, pdf: bool) -> None:
    """What vizpub.py leaves in cope-drafts/vizpub/<slug>/ (same layout as static/)."""
    write(review / "images" / "vizpub" / f"{slug}.png", "png")
    write(review / "images" / "vizpub" / f"{slug}.svg", "<svg/>")
    write(review / "images" / "vizpub" / f"{slug}.mmd", "graph LR; a-->b")
    for i in range(4):
        write(review / "images" / "slides" / f"{slug}-0{i + 1}.svg", "<svg/>")
    if pdf:
        write(review / "slides" / f"{slug}.pdf", "%PDF")
    write(review / "slides" / f"{slug}.html",
          vizpub.slides_html(slug, 4, section, f"{slug}.pdf" if pdf else None))


class PostAssets(unittest.TestCase):
    def test_only_what_the_post_references_is_published(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            review = Path(d) / "review"
            vizpub_tree(review, "s", "experiments", pdf=True)
            post = "---\ntitle: t\n---\n![A diagram](/images/vizpub/s.png)\n*A diagram*\n"
            self.assertEqual(post_assets.referenced(post, review), ["images/vizpub/s.png"])

    def test_a_referenced_page_brings_its_own_files(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            review = Path(d) / "review"
            vizpub_tree(review, "s", "experiments", pdf=False)
            write(review / "slides" / "s.pdf", "%PDF")  # present, but the page does not link it
            post = "![d](/images/vizpub/s.png)\n[slides](https://zhanyl-tech.github.io/slides/s.html)\n"
            got = post_assets.referenced(post, review)
            self.assertEqual(got, ["images/slides/s-01.svg", "images/slides/s-02.svg", "images/slides/s-03.svg",
                                   "images/slides/s-04.svg", "images/vizpub/s.png", "slides/s.html"])

    def test_path_must_match_whole(self) -> None:
        rel = "images/vizpub/s.png"
        self.assertTrue(post_assets.mentions("![x](/images/vizpub/s.png)", rel))
        self.assertTrue(post_assets.mentions('<img src="/images/vizpub/s.png">', rel))
        self.assertTrue(post_assets.mentions("https://zhanyl-tech.github.io/images/vizpub/s.png", rel))
        self.assertFalse(post_assets.mentions("![x](/x/images/vizpub/s.png)", rel))
        self.assertFalse(post_assets.mentions("![x](/images/vizpub/s.png.bak)", rel))
        self.assertFalse(post_assets.mentions("images/vizpub/s.png without a leading slash", rel))

    def test_cli_lists_both_sides(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            review = Path(d) / "review"
            vizpub_tree(review, "s", "notes", pdf=False)
            post = write(Path(d) / "s.md", "![d](/images/vizpub/s.png)\n")
            run = [sys.executable, str(SCRIPTS / "post_assets.py"), str(post), "--review-dir", str(review)]
            used = subprocess.run(run + ["-0"], capture_output=True, text=True, check=True).stdout
            self.assertEqual(used, "images/vizpub/s.png\0")
            left = subprocess.run(run + ["--unreferenced"], capture_output=True, text=True, check=True).stdout
            self.assertIn("slides/s.html", left.splitlines())
            self.assertNotIn("images/vizpub/s.png", left.splitlines())

    def test_weekly_copies_only_the_listed_assets(self) -> None:
        weekly = (SCRIPTS / "weekly.sh").read_text(encoding="utf-8")
        self.assertIn("scripts/post_assets.py", weekly)
        self.assertNotIn('find "$REVIEW_DIR"', weekly)
        # the listing comes before the slug confirmation, not after it
        self.assertLess(weekly.index("scripts/post_assets.py"), weekly.index("read -r CONFIRM"))


class VizpubSlides(unittest.TestCase):
    def test_post_link_follows_the_section_and_pdf_needs_a_pdf(self) -> None:
        html = vizpub.slides_html("s", 4, "experiments")
        self.assertIn('href="/experiments/s/"', html)
        self.assertNotIn("blog/", html)
        self.assertNotIn(".pdf", html)
        self.assertIn('href="./s.pdf"', vizpub.slides_html("s", 4, "notes", "s.pdf"))

    def published_site(self, root: Path, section: str, slug: str, pdf: bool, html: str | None = None) -> None:
        """A built site holding one vizpub post and everything weekly.sh would copy for it."""
        review = root.parent / "review"
        vizpub_tree(review, slug, section, pdf)
        if html is not None:
            write(review / "slides" / f"{slug}.html", html)
        post = f"![d](/images/vizpub/{slug}.png)\n[Slides](/slides/{slug}.html)\n"
        for rel in post_assets.referenced(post, review):
            dest = root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(review / rel, dest)
        write(root / section / slug / "index.html",
              f'<img src="/images/vizpub/{slug}.png"><a href="/slides/{slug}.html">Slides</a>')

    def test_generated_slides_pass_the_link_check(self) -> None:
        # vizpub's default section, with and without Chrome (no PDF)
        for pdf in (False, True):
            with tempfile.TemporaryDirectory() as d:
                root = Path(d) / "site"
                self.published_site(root, "experiments", "paged-kv-demo", pdf)
                self.assertEqual(linkcheck.main([str(root)]), 0, f"pdf={pdf}")

    def test_the_old_hard_coded_links_fail_it(self) -> None:
        old = ('<p class="meta">PDF: <a href="./s.pdf">./s.pdf</a> · '
               'Post: <a href="../../blog/s/">blog/s/</a></p>')
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "site"
            self.published_site(root, "experiments", "s", pdf=False, html=old)
            self.assertEqual(linkcheck.main([str(root)]), 1)


class SvgWellFormed(unittest.TestCase):
    """A browser draws nothing for an SVG that is not well-formed XML.

    LServe Figure 2 carried a stray </text> and never rendered at all, which
    also hid the withdrawn bit-width in it from anyone checking the page.
    """

    def test_every_published_svg_parses(self) -> None:
        svgs = sorted((ROOT / "static").rglob("*.svg"))
        self.assertTrue(svgs)
        for svg in svgs:
            with self.subTest(svg=svg.relative_to(ROOT).as_posix()):
                ET.parse(svg)


class Python39(unittest.TestCase):
    """python3 on macOS is 3.9, and the README runs these tests with it.

    `X | None` in an annotation is evaluated at import on 3.9 and raises
    TypeError unless the module has `from __future__ import annotations`.
    """

    def test_union_annotations_have_the_future_import(self) -> None:
        for script in sorted(SCRIPTS.glob("*.py")):
            tree = ast.parse(script.read_text(encoding="utf-8"))
            future = any(
                isinstance(node, ast.ImportFrom) and node.module == "__future__"
                and any(a.name == "annotations" for a in node.names)
                for node in tree.body
            )
            annotations = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    args = node.args.posonlyargs + node.args.args + node.args.kwonlyargs
                    args += [a for a in (node.args.vararg, node.args.kwarg) if a]
                    annotations += [a.annotation for a in args if a.annotation] + [node.returns]
                elif isinstance(node, ast.AnnAssign):
                    annotations.append(node.annotation)
            uses_union = any(
                isinstance(sub, ast.BinOp) and isinstance(sub.op, ast.BitOr)
                for ann in annotations if ann is not None for sub in ast.walk(ann)
            )
            with self.subTest(script=script.name):
                self.assertTrue(future or not uses_union, "PEP 604 annotation without the future import")


class DefaultCardAlt(unittest.TestCase):
    def test_alt_text_is_the_cards_own_words(self) -> None:
        config = (ROOT / "hugo.yaml").read_text(encoding="utf-8")
        m = re.search(r'^\s*defaultCardAlt:\s*"([^"]+)"', config, re.MULTILINE)
        self.assertIsNotNone(m, "hugo.yaml params.defaultCardAlt is missing")
        self.assertIn(ogimage.DEFAULT_CARD_TITLE, m.group(1))
        partial = (ROOT / "layouts" / "partials" / "templates" / "twitter_cards.html").read_text(encoding="utf-8")
        self.assertIn("site.Params.defaultCardAlt", partial)


class StaticDiagrams(unittest.TestCase):
    def test_animations_removed_and_nothing_else(self) -> None:
        svg = ('<svg><rect opacity="1"><animate attributeName="opacity" values="1;0;1" '
               'dur="1s" repeatCount="indefinite"/></rect><text>keep</text></svg>')
        out = static_diagrams.still(svg)
        self.assertNotIn("animate", out)
        self.assertEqual(re.sub(r"\s", "", out), '<svg><rectopacity="1"></rect><text>keep</text></svg>')

    def test_shipped_twins_are_current(self) -> None:
        self.assertEqual(static_diagrams.main(["--check"]), 0)


if __name__ == "__main__":
    unittest.main()
