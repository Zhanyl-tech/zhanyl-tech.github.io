#!/usr/bin/env python3
"""
check_content.py — content rules the Hugo build cannot enforce
==============================================================

Four rules, all about not publishing something by accident:

1. A published page (no `draft: true`) must not contain vizpub's review
   marker. vizpub.py writes the marker into every generated post in place of
   a disclosure; it stays until a person has read the post and replaced it.
   Hugo would happily render it, so this check is what makes "reviewed before
   publishing" a gate rather than a habit.
2. Every published project page declares `stage:` as exactly one of built,
   partial or planned. The homepage, the system map and the project list use
   those three words, and a project that says none of them is how an unbuilt
   component ended up looking like a running one.
3. A published page does not name a working branch (`improve/…`,
   `publish/…`) outside an HTML comment. Branches are deleted after they
   merge, so a result pinned to one cannot be reproduced for long; name a
   commit or a tag, as the backfill write-up does with `c02b52f`.
4. Wording this site withdrew stays withdrawn (WITHDRAWN below). Each entry
   was published, or about to be, and then corrected because the source or
   the repository said otherwise. The rule stops it coming back through a
   copy from an older draft or another repository's README.
   content/corrections.md is exempt: quoting what was withdrawn is its job.

HTML comments are ignored by rules 3 and 4: they hold owner notes, and the
minified build strips them. Exit 1 on any violation. Standard library only; run it in CI before the
build, and from weekly.sh before a publish.

    python3 scripts/check_content.py
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
REVIEW_MARKER = "VIZPUB-REVIEW-TODO"  # keep in step with scripts/vizpub.py
STAGES = {"built", "partial", "planned"}
BRANCH_REF = re.compile(r"(?<![\w/.-])(?:improve|publish)/[\w.-]+")
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)

_PAGES = ("content/**/*.md",)
_SITE_TEXT = (
    "content/**/*.md",
    "hugo.yaml",
    "layouts/**/*.html",
    "static/images/*.svg",
    "static/images/diagrams/*.svg",
)

# (pattern, files it must not appear in, relative to the repository root, why).
# Patterns match across line breaks where the text is wrapped.
WITHDRAWN: tuple[tuple[str, tuple[str, ...], str], ...] = (
    (r"does not have to\s+maintain a\s+watch", _PAGES,
     "misquotes kubernetes.io's Secret page, which says the kubelet \"does not "
     "need to maintain a watch on any Secrets that are marked as immutable\""),
    (r"\bINT4\b", ("static/images/figures/lserve-*.svg",),
     "the LServe post withdrew the KV bit-width; the author could not find it stated in the paper's text"),
    (r"keeps\s+serving\s+the\s+node's|served\s+a\s+stale\s+cached\s+copy", _SITE_TEXT,
     "that the kubelet serves slurmd a cached key is a hypothesis, not an observation "
     "(slinky-gitops page)"),
    (r"shared\s+HCA\s+is\s+never\s+attributed|refuses?\s+to\s+attribute\s+a\s+shared\s+device"
     r"|refuse\s+when\s+a\s+device\s+is\s+shared", _SITE_TEXT,
     "ib-slurm-exporter refuses only when it can see a port is shared; kernel RDMA "
     "users are invisible to its default mode"),
    (r"failed\s+<code>nvidia-smi</code>\s+query\s+exits\s+0"
     r"|never\s+(?:for|on)\s+a\s+failed\s+query(?!\s+(?:without|that\s+carries))", _SITE_TEXT,
     "nvidia-smi exit codes 8, 10, 14 and 15 are hardware evidence and do drain "
     "(epilog-gpu-validator rule 1)"),
    (r"Slurm\s+sees\s+allocations,\s+not\s+GPUs", _SITE_TEXT,
     "Slurm can record per-job GPU utilisation; it does not act on it (gpu-reaper page)"),
    (r"K0\s+\+\s+degenerate\s+baselines\s+measured", ("hugo.yaml",),
     "D-preempt has no cluster run; only K0, D-fifo, D-random and D-largest were measured"),
    (r"read-only\s+guard\s+\+\s+MCP\s+server\s+built", ("static/images/architecture.svg",),
     "cluster-sre-agent has no MCP server; slurm-mcp is a separate, built project"),
    (r"GPU\s+clusters,\s+(?:<em>)?measured|fleet\s+health,\s+measured",
     ("hugo.yaml", "layouts/**/*.html", "scripts/ogimage.py"),
     "the fleet-health tools are tested on simulators and synthetic trees, not measured "
     "on hardware"),
    (r"doing\s+real\s+work\s+in\s+the\s+evaluation\s+harness", _PAGES,
     "research-platform's evaluation harness is planned, not built"),
)
EXEMPT = {"content/corrections.md"}


def front_matter(text: str) -> dict[str, str]:
    """Top-level scalar keys of YAML front matter, enough for these rules."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    out: dict[str, str] = {}
    for line in text[3:end].splitlines():
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*?)\s*(?:#.*)?$", line)
        if m:
            out[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return out


def check(content: Path = CONTENT) -> list[str]:
    problems: list[str] = []
    for md in sorted(content.rglob("*.md")):
        text = md.read_text(encoding="utf-8")
        meta = front_matter(text)
        if meta.get("draft", "false").lower() == "true":
            continue
        rel = md.relative_to(content.parent).as_posix()
        if REVIEW_MARKER in text:
            problems.append(f"{rel}: published with the {REVIEW_MARKER} marker; review it and replace the marker")
        if md.parent.name == "projects" and md.name != "_index.md":
            stage = meta.get("stage", "")
            if stage not in STAGES:
                problems.append(f"{rel}: stage must be one of {sorted(STAGES)}, got {stage!r}")
            if not meta.get("status"):
                problems.append(f"{rel}: no status line in front matter")
        for branch in sorted(set(BRANCH_REF.findall(_COMMENT.sub("", text)))):
            problems.append(f"{rel}: names the working branch {branch!r}; cite a commit or tag instead")
    return problems


def check_withdrawn(root: Path = ROOT) -> list[str]:
    """Rule 4: withdrawn wording in any published file it is listed for."""
    problems: list[str] = []
    for pattern, globs, why in WITHDRAWN:
        regex = re.compile(pattern)
        files = sorted({f for g in globs for f in root.glob(g) if f.is_file()})
        for path in files:
            rel = path.relative_to(root).as_posix()
            if rel in EXEMPT:
                continue
            text = path.read_text(encoding="utf-8")
            if path.suffix == ".md" and front_matter(text).get("draft", "false").lower() == "true":
                continue
            m = regex.search(_COMMENT.sub("", text))
            if m:
                found = " ".join(m.group(0).split())
                problems.append(f"{rel}: withdrawn wording {found!r}: {why}")
    return problems


def main() -> int:
    problems = check() + check_withdrawn()
    for p in problems:
        print(p)
    if problems:
        return 1
    print("content checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
