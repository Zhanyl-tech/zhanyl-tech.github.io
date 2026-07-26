#!/usr/bin/env python3
"""
social.py — turn a published post into ready-to-post social drafts
==================================================================

Replaces cope.sh's bracket-placeholder templates. Those required you to fill in
"[Key insight 1]" by hand every week, which is exactly the friction that stops a
publishing habit. This reads the actual post and writes drafts you can post
after a 60-second review.

Two modes, chosen automatically:

  ANTHROPIC_API_KEY set    Claude drafts from the full post text.
  no key                   Deterministic extraction — headings, the numbers in
                           the post, and the first substantive paragraph. Less
                           polished, still specific, never a placeholder.

Usage:
    python3 scripts/social.py content/blog/2026-07-26-post.md
    python3 scripts/social.py content/blog/2026-07-26-post.md --hn
    python3 scripts/social.py content/blog/2026-07-26-post.md --copy linkedin
    python3 scripts/social.py content/blog/2026-07-26-post.md --copy x --open
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DRAFTS = ROOT / "cope-drafts"
SITE_URL = "https://zhanyl-tech.github.io"

MODEL = "claude-opus-5"

SECTION_URL = {"blog": "blog", "experiments": "experiments", "notes": "notes"}

# Claude returns exactly this shape, so the writer below never has to parse prose.
DRAFT_SCHEMA = {
    "type": "object",
    "properties": {
        "linkedin": {
            "type": "object",
            "properties": {
                "hook": {
                    "type": "string",
                    "description": "First 2 lines — visible before LinkedIn's 'see more' fold.",
                },
                "body": {
                    "type": "string",
                    "description": "Full post text. No links (they suppress reach). 900-1300 characters.",
                },
                "first_comment": {
                    "type": "string",
                    "description": "The comment carrying the article link.",
                },
            },
            "required": ["hook", "body", "first_comment"],
            "additionalProperties": False,
        },
        "x": {
            "type": "object",
            "properties": {
                "tweets": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "5-7 tweets, each under 280 characters. Tweet 1 is the hook.",
                }
            },
            "required": ["tweets"],
            "additionalProperties": False,
        },
        "hn": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Factual, non-hyped HN title, under 80 characters.",
                },
                "comment": {
                    "type": "string",
                    "description": "Author's context comment, 3-5 sentences.",
                },
            },
            "required": ["title", "comment"],
            "additionalProperties": False,
        },
    },
    "required": ["linkedin", "x", "hn"],
    "additionalProperties": False,
}

VOICE = """\
You write social copy for Zhanyl Abdybaeva, an ML infrastructure and quantitative
finance engineer at a quant trading firm. She writes about GPU clusters, inference
systems (vLLM, TensorRT-LLM), distributed training, Slurm/HPC scheduling, and the
systems engineering behind production AI.

Voice rules — these matter more than polish:
- Lead with a concrete technical finding, never a question or a "Here's why X matters".
- Use the actual numbers, tool names, and versions from the post. Specificity is the
  entire credibility mechanism; a generic post is worse than no post.
- No emoji. No "🚀". No "Thoughts?". No "Let that sink in." No engagement bait.
- No em-dashes. Short sentences. Practitioner-to-practitioner register.
- Never claim experience or results the post does not contain. If the post is a paper
  explainer, frame it as reading a paper, not as production experience.
- It is fine to be plain. It is not fine to be vague.
"""


def parse_post(path: Path) -> dict[str, object]:
    """Split frontmatter from body. Only the scalar keys we need are read."""
    text = path.read_text(encoding="utf-8")
    meta: dict[str, str] = {}
    body = text

    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            for line in text[3:end].splitlines():
                line = line.strip()
                if not line or line.startswith("#") or ":" not in line:
                    continue
                key, _, value = line.partition(":")
                meta[key.strip()] = value.strip().strip('"').strip("'")
            body = text[end + 4 :]

    return {"meta": meta, "body": body.strip()}


def post_url(path: Path) -> str:
    section = SECTION_URL.get(path.parent.name, path.parent.name)
    return f"{SITE_URL}/{section}/{path.stem}/"


def extract_signals(body: str) -> dict[str, list[str]]:
    """Pull the concrete bits a draft should be built from."""
    headings = re.findall(r"^#{2,3}\s+(.+)$", body, re.MULTILINE)

    # Sentences carrying a number, percentage, or unit — the quotable claims.
    prose = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
    prose = re.sub(r"^\s*[-*|>]\s?", "", prose, flags=re.MULTILINE)
    numeric = [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+", prose)
        if re.search(r"\d+(\.\d+)?\s*(%|x|×|GB|MB|ms|s\b|TB|GPU|tokens?/s|k\b)", s)
        and 40 < len(s.strip()) < 240
    ]

    paragraphs = [
        p.strip()
        for p in prose.split("\n\n")
        if len(p.strip()) > 120 and not p.strip().startswith(("#", "!", "<"))
    ]

    return {
        "headings": headings[:6],
        "numeric": numeric[:6],
        "paragraphs": paragraphs[:3],
    }


def generate_with_claude(meta: dict, body: str, url: str) -> dict | None:
    """Draft via the Messages API. Returns None if the SDK or key is unavailable."""
    try:
        import anthropic
    except ImportError:
        print("  ! anthropic SDK not installed — using extraction fallback")
        return None

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("  ! ANTHROPIC_API_KEY not set — using extraction fallback")
        return None

    client = anthropic.Anthropic()

    # Long posts get truncated; the opening carries the thesis and the numbers.
    excerpt = body[:24000]

    prompt = f"""{VOICE}

Below is a post that just went live at {url}.

Write the social drafts for it. Every claim must trace back to the post text.

TITLE: {meta.get('title', '')}
DESCRIPTION: {meta.get('description', '')}
TAGS: {meta.get('tags', '')}

POST:
{excerpt}
"""

    try:
        with client.messages.stream(
            model=MODEL,
            max_tokens=16000,
            thinking={"type": "adaptive"},
            output_config={
                "effort": "medium",
                "format": {"type": "json_schema", "schema": DRAFT_SCHEMA},
            },
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            response = stream.get_final_message()
    except Exception as exc:  # noqa: BLE001 — any API failure falls back cleanly
        print(f"  ! Claude call failed ({exc.__class__.__name__}) — using fallback")
        return None

    if response.stop_reason == "refusal":
        print("  ! request was declined — using extraction fallback")
        return None

    text = next((b.text for b in response.content if b.type == "text"), None)
    if not text:
        return None

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        print("  ! could not parse model output — using extraction fallback")
        return None


def generate_by_extraction(meta: dict, body: str, url: str) -> dict:
    """No-API fallback: assemble drafts from the post's own sentences."""
    title = meta.get("title", "Untitled")
    description = meta.get("description", "")
    signals = extract_signals(body)

    points = signals["numeric"] or signals["headings"] or signals["paragraphs"][:3]
    bullets = "\n".join(f"→ {p.rstrip('.')}" for p in points[:3])

    opener = description or (signals["paragraphs"][0][:200] if signals["paragraphs"] else title)

    tags = [t.strip() for t in meta.get("tags", "").strip("[]").split(",") if t.strip()]
    hashtags = " ".join(
        "#" + "".join(w.capitalize() for w in t.replace("-", " ").split())
        for t in tags[:5]
    )

    tweets = [opener]
    tweets += [p for p in points[:4]]
    tweets.append(f"Full writeup:\n\n{url}")

    return {
        "linkedin": {
            "hook": opener,
            "body": f"{opener}\n\n{bullets}\n\n{hashtags}".strip(),
            "first_comment": f"Full writeup with the details: {url}",
        },
        "x": {"tweets": [t[:275] for t in tweets]},
        "hn": {
            "title": title,
            "comment": (
                f"{description}\n\nWrote this up after working through the material; "
                "happy to answer questions about the setup or the numbers."
            ),
        },
    }


def write_drafts(slug: str, drafts: dict, url: str, want_hn: bool) -> list[Path]:
    written: list[Path] = []

    li = drafts["linkedin"]
    li_path = DRAFTS / "linkedin" / f"{slug}.md"
    li_path.parent.mkdir(parents=True, exist_ok=True)
    li_path.write_text(
        f"""# LinkedIn — {slug}

## POST TEXT (paste as-is; attach the OG card as a native image)

{li['body']}

---

## FIRST COMMENT (post immediately after publishing — the link goes here, not above)

{li['first_comment']}

---

## CHECKLIST
- [ ] Read it once. Cut anything you would not say out loud.
- [ ] Attach static/images/og/{slug}.png as a native image
- [ ] Post Tue-Thu, 8-10 AM ET
- [ ] Add the first comment within 60 seconds
""",
        encoding="utf-8",
    )
    written.append(li_path)

    x_path = DRAFTS / "x" / f"{slug}.md"
    x_path.parent.mkdir(parents=True, exist_ok=True)
    numbered = "\n\n".join(
        f"**{i}/{len(drafts['x']['tweets'])}** ({len(t)} chars)\n{t}"
        for i, t in enumerate(drafts["x"]["tweets"], 1)
    )
    x_path.write_text(
        f"""# X thread — {slug}

{numbered}

---

## CHECKLIST
- [ ] Attach the OG card to tweet 1
- [ ] Every tweet under 280 characters (counts shown above)
- [ ] Post Wed, 8-10 AM ET
""",
        encoding="utf-8",
    )
    written.append(x_path)

    if want_hn:
        hn = drafts["hn"]
        hn_path = DRAFTS / "hn" / f"{slug}.md"
        hn_path.parent.mkdir(parents=True, exist_ok=True)
        hn_path.write_text(
            f"""# Hacker News — {slug}

## TITLE
{hn['title']}

## URL
{url}

## FIRST COMMENT (as the author)
{hn['comment']}

---

## CHECKLIST
- [ ] Deep dives only. Skip this for lab notes.
- [ ] Title stays factual — HN punishes hype hard
- [ ] Submit: https://news.ycombinator.com/submit
""",
            encoding="utf-8",
        )
        written.append(hn_path)

    return written


def copy_and_open(drafts: dict, target: str, url: str, do_open: bool) -> None:
    """Put the draft on the clipboard and optionally open the compose window."""
    if target == "linkedin":
        payload = drafts["linkedin"]["body"]
        compose = "https://www.linkedin.com/feed/?shareActive=true"
    elif target == "x":
        payload = drafts["x"]["tweets"][0]
        compose = "https://x.com/compose/post?text=" + urllib.parse.quote(payload)
    else:
        payload = f"{drafts['hn']['title']}\n{url}"
        compose = "https://news.ycombinator.com/submit"

    try:
        subprocess.run(["pbcopy"], input=payload.encode("utf-8"), check=True)
        print(f"  ✓ {target} draft copied to clipboard")
    except (FileNotFoundError, subprocess.CalledProcessError):
        print(f"  ! could not reach pbcopy — draft is on disk")

    if do_open:
        subprocess.run(["open", compose], check=False)
        print(f"  ✓ opened {target} compose window")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate social drafts from a post.")
    parser.add_argument("post", help="Path to the markdown post")
    parser.add_argument("--hn", action="store_true", help="Also draft a Hacker News submission")
    parser.add_argument("--copy", choices=["linkedin", "x", "hn"], help="Copy a draft to the clipboard")
    parser.add_argument("--open", action="store_true", help="Open the compose window for --copy")
    args = parser.parse_args()

    path = Path(args.post)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        print(f"error: no such post: {args.post}", file=sys.stderr)
        return 1

    parsed = parse_post(path)
    meta, body = parsed["meta"], parsed["body"]
    url = post_url(path)

    print(f"  Drafting from: {meta.get('title', path.stem)}")

    drafts = generate_with_claude(meta, body, url) or generate_by_extraction(meta, body, url)

    for written in write_drafts(path.stem, drafts, url, want_hn=args.hn):
        print(f"  ✓ {written.relative_to(ROOT)}")

    if args.copy:
        copy_and_open(drafts, args.copy, url, args.open)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
