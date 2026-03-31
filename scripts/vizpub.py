#!/usr/bin/env python3
"""
VIZPUB v2 — publisher-manager workflow
======================================

Interactive or flag-driven content pipeline for:
- Blog deep dives
- Lab Notes
- Notes

Generates:
1. Diagram source + PNG
2. Draft post
3. Learning summary
4. LinkedIn draft (optional)
5. X thread draft (optional)
6. Hacker News draft (optional)
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from textwrap import dedent
from typing import Any

try:
    import anthropic
except ImportError:
    print("Install anthropic: .venv/bin/python -m pip install anthropic")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("Install requests: .venv/bin/python -m pip install requests")
    sys.exit(1)


HUGO_ROOT = Path(__file__).parent.parent
CONTENT_DIR = HUGO_ROOT / "content"
STATIC_DIR = HUGO_ROOT / "static" / "images" / "vizpub"
SLIDES_DIR = HUGO_ROOT / "static" / "images" / "slides"
SLIDES_HTML_DIR = HUGO_ROOT / "static" / "slides"
DRAFTS_DIR = HUGO_ROOT / "cope-drafts"
MODEL = "claude-opus-4-5"
DEFAULT_SITE_URL = "https://zhanyl-tech.github.io"
SECTION_ALIASES = {
    "blog": "blog",
    "experiments": "experiments",
    "lab-notes": "experiments",
    "labnotes": "experiments",
    "lab_notes": "experiments",
    "notes": "notes",
}
SECTION_LABELS = {
    "blog": "blog deep dive",
    "experiments": "lab note",
    "notes": "note",
}
TARGET_CHOICES = {"linkedin", "x", "hn"}
DEFAULT_TARGETS = ["linkedin", "x"]

MERMAID_CONFIG = {
    "theme": "base",
    "themeVariables": {
        "primaryColor": "#E8F4FD",
        "primaryTextColor": "#1a1a2e",
        "primaryBorderColor": "#4A90D9",
        "secondaryColor": "#FFF3E0",
        "secondaryTextColor": "#1a1a2e",
        "secondaryBorderColor": "#F5A623",
        "tertiaryColor": "#E8F5E9",
        "tertiaryTextColor": "#1a1a2e",
        "tertiaryBorderColor": "#4CAF50",
        "lineColor": "#5D6D7E",
        "textColor": "#1a1a2e",
        "fontSize": "14px",
        "fontFamily": "Inter, system-ui, sans-serif",
    },
}


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text[:60].rstrip("-")


def load_local_env() -> None:
    env_file = HUGO_ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def resolve_mmdc_binary() -> str:
    local_mmdc = HUGO_ROOT / "node_modules" / ".bin" / "mmdc"
    if local_mmdc.exists():
        return str(local_mmdc)
    global_mmdc = shutil.which("mmdc")
    if global_mmdc:
        return global_mmdc
    return "mmdc"


def require_api_key() -> None:
    load_local_env()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: Set ANTHROPIC_API_KEY environment variable")
        print("You can also add it to a local .env file in the repo root.")
        print("  export ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)


def normalize_section(section: str) -> str:
    normalized = SECTION_ALIASES.get(section.strip().lower())
    if not normalized:
        raise ValueError(f"Invalid section: {section}")
    return normalized


def split_csv_values(values: list[str] | None) -> list[str]:
    if not values:
        return []
    items: list[str] = []
    for value in values:
        parts = [part.strip() for part in value.split(",")]
        items.extend([part for part in parts if part])
    return items


def parse_targets(values: list[str] | None) -> list[str]:
    parsed = [value.lower() for value in split_csv_values(values)]
    if not parsed:
        return list(DEFAULT_TARGETS)
    invalid = [value for value in parsed if value not in TARGET_CHOICES]
    if invalid:
        raise ValueError(f"Invalid targets: {', '.join(invalid)}")
    seen: list[str] = []
    for target in parsed:
        if target not in seen:
            seen.append(target)
    return seen


def prompt_text(label: str, default: str = "", allow_blank: bool = False) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        value = input(f"{label}{suffix}: ").strip()
        if value:
            return value
        if default:
            return default
        if allow_blank:
            return ""


def prompt_interactively() -> dict[str, Any]:
    print("VIZPUB interactive mode")
    print("=======================")
    print("Write once, then generate a post, diagram, and promotion drafts.\n")

    topic = prompt_text("Topic")
    focus = prompt_text("Specific angle / focus", allow_blank=True)
    section_input = prompt_text("Section (blog / lab-notes / notes)", "lab-notes")
    section = normalize_section(section_input)
    papers_input = prompt_text("Paper or reference URLs (comma-separated, optional)", allow_blank=True)
    papers = split_csv_values([papers_input]) if papers_input else []
    targets_input = prompt_text("Promotion targets (comma-separated: linkedin,x,hn)", "linkedin,x")
    targets = parse_targets([targets_input])
    site_url = prompt_text("Site URL", DEFAULT_SITE_URL)

    return {
        "topic": topic,
        "focus": focus,
        "section": section,
        "papers": papers,
        "targets": targets,
        "site_url": site_url,
        "slug": "",
    }


def fetch_reference_context(url: str) -> str:
    if "arxiv.org" in url:
        arxiv_url = url.replace("/pdf/", "/abs/").rstrip(".pdf")
        try:
            resp = requests.get(arxiv_url, timeout=15)
            text = resp.text
            title_match = re.search(r'<meta name="citation_title" content="([^"]+)"', text)
            abstract_match = re.search(
                r'<blockquote class="abstract[^"]*">\s*<span class="descriptor">Abstract:</span>\s*(.*?)</blockquote>',
                text,
                re.DOTALL,
            )
            title = title_match.group(1) if title_match else "Unknown"
            abstract = abstract_match.group(1).strip() if abstract_match else ""
            abstract = re.sub(r"<[^>]+>", "", abstract).strip()
            return f"Title: {title}\nURL: {url}\nAbstract: {abstract}"
        except Exception as exc:
            return f"URL: {url}\nNote: failed to fetch arXiv abstract ({exc})"

    try:
        resp = requests.get(url, timeout=15)
        text = re.sub(r"<script[\s\S]*?</script>", " ", resp.text, flags=re.I)
        text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        snippet = text[:1800]
        return f"URL: {url}\nSnippet: {snippet}"
    except Exception as exc:
        return f"URL: {url}\nNote: failed to fetch page ({exc})"


def build_reference_context(urls: list[str]) -> str:
    if not urls:
        return ""
    chunks = []
    for idx, url in enumerate(urls, start=1):
        print(f"📄 Fetching reference {idx}/{len(urls)}: {url}")
        chunks.append(f"[Reference {idx}]\n{fetch_reference_context(url)}")
    return "\n\n".join(chunks)


def call_claude_json(system_prompt: str, user_prompt: str, max_tokens: int = 5000) -> dict[str, Any]:
    client = anthropic.Anthropic()
    message = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Error parsing Claude JSON response: {exc}")
        print(raw[:1200])
        sys.exit(1)


def refine_brief(topic: str, focus: str, section: str, targets: list[str], references: str) -> dict[str, Any]:
    system = dedent(
        """\
        You are a publisher-manager for a senior ML infrastructure and quantitative systems engineer.
        Your job is to sharpen raw topics into publishable technical angles.

        Return valid JSON with exactly these keys:
        - refined_topic
        - suggested_slug
        - audience_angle
        - why_this_matters
        - teaching_goal
        - recommended_section
        - key_questions (array of 3-5 strings)

        Rules:
        - Make the topic sharper, narrower, and more publishable.
        - The public voice should sound like an intelligent research engineer, not a learner journal.
        - Prioritize clarity, specificity, and technical usefulness.
        - If the topic is too broad, narrow it.
        - Prefer titles/angles that help readers understand hard things quickly.
        - recommended_section must be one of: blog, experiments, notes
        """
    )

    user = dedent(
        f"""\
        Raw topic: {topic}
        Focus: {focus or "(none provided)"}
        Requested section: {section}
        Promotion targets: {", ".join(targets)}

        References:
        {references or "(no references provided)"}
        """
    )
    return call_claude_json(system, user, max_tokens=1800)


def generate_content_package(
    brief: dict[str, Any],
    section: str,
    targets: list[str],
    references: str,
) -> dict[str, Any]:
    section_name = SECTION_LABELS[section]
    section_word_target = {
        "blog": "1600-2600 words",
        "experiments": "700-1300 words",
        "notes": "350-700 words",
    }[section]
    targets_text = ", ".join(targets)

    system = dedent(
        f"""\
        You are a senior HPC / ML infrastructure engineer writing for other senior engineers.
        You are NOT an AI assistant summarizing papers. You are a practitioner sharing what you learned.

        Voice rules — write as a human practitioner, not an AI:
        - Write short, direct sentences. Vary sentence length. Use plain words.
        - First-person is fine ("my take", "I've seen this", "the part that surprised me").
        - Start sections with the concrete point, not a meta-statement about what you're going to explain.
        - Use "you" to speak directly to the reader.
        - Never hedge with "it's worth noting", "it is important to understand", "let's explore".
        - End sections with a clear implication or opinion, not a neutral summary.

        BANNED words and phrases (do NOT use any of these):
        dive into, delve into, it's worth noting, crucial, leverage, utilize, robust, seamless,
        comprehensive, groundbreaking, fascinating, paradigm, at its core, needless to say,
        as we can see, in conclusion, furthermore, moreover, essentially, basically, cutting-edge,
        state-of-the-art, the world of, a testament to, in this post we will, let's explore,
        it becomes clear, it is important to note, the key insight is, this allows us to.

        Do NOT write like a learner diary. Do NOT lower authority.
        The writing should feel composed, experienced, and opinionated.

        The post type is a {section_name}.
        Target length: {section_word_target}.
        Promotion targets: {targets_text}.

        Return valid JSON with exactly these keys:
        - title
        - description
        - tags
        - diagram_caption
        - mermaid
        - post_body
        - learning_summary
        - linkedin_text
        - x_thread
        - hn_title
        - hn_text

        Mermaid rules (used as fallback diagram):
        - 6-12 nodes max
        - flowchart TD or LR
        - short labels, clear flow
        - prioritize one concept per diagram

        Writing structure:
        - Open with the problem or the tension (one short paragraph, no preamble).
        - Cover the mechanism clearly — what it does, why that design choice.
        - Point out the thing most people miss or get wrong.
        - Close with practical implications for someone building real systems.

        LinkedIn rules:
        - No external links in body text
        - 3-6 short paragraphs or bullet groups
        - Hook: one punchy line that makes engineers want to keep reading
        - Use → for bullets, not •
        - First comment holds the link

        X rules:
        - 4-6 tweets
        - Tweet 1: hook + 🧵 marker
        - Each tweet: one clean idea, under 280 chars
        - Last tweet: link

        HN rules:
        - factual title under 80 chars
        - intro: one paragraph, why this is useful to infra/ML engineers

        If a promotion target is not requested, still return the key with an empty string or empty array.
        """
    )

    user = dedent(
        f"""\
        Refined topic: {brief.get("refined_topic", "")}
        Audience angle: {brief.get("audience_angle", "")}
        Why this matters: {brief.get("why_this_matters", "")}
        Teaching goal: {brief.get("teaching_goal", "")}
        Key questions: {json.dumps(brief.get("key_questions", []))}
        Recommended section: {brief.get("recommended_section", "")}

        References:
        {references or "(no references provided)"}
        """
    )
    return call_claude_json(system, user, max_tokens=7000)


def normalize_payload(payload: dict[str, Any], targets: list[str]) -> dict[str, Any]:
    payload["tags"] = payload.get("tags") or []
    if not isinstance(payload["tags"], list):
        payload["tags"] = [str(payload["tags"])]

    payload["learning_summary"] = payload.get("learning_summary") or []
    if not isinstance(payload["learning_summary"], list):
        payload["learning_summary"] = [str(payload["learning_summary"])]

    payload["x_thread"] = payload.get("x_thread") or []
    if not isinstance(payload["x_thread"], list):
        payload["x_thread"] = [str(payload["x_thread"])]

    for key in ["title", "description", "diagram_caption", "mermaid", "post_body", "linkedin_text", "hn_title", "hn_text"]:
        payload[key] = str(payload.get(key, "")).strip()

    if "linkedin" not in targets:
        payload["linkedin_text"] = ""
    if "x" not in targets:
        payload["x_thread"] = []
    if "hn" not in targets:
        payload["hn_title"] = ""
        payload["hn_text"] = ""
    return payload


def call_claude_text(system_prompt: str, user_prompt: str, max_tokens: int = 8000) -> str:
    client = anthropic.Anthropic()
    message = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return message.content[0].text.strip()


SVG_STYLE_GUIDE = """\
ByteByteGo-style SVG rules (follow precisely):
- Canvas: white background (#FFFFFF)
- Header band: dark navy (#1A2B6D or similar) with white text, full width, ~88–140px tall
- Section cards: colored rectangle with matching darker header bar, rounded corners (rx="20")
- Color palette per card: blue (#4285F4 / #E8F0FE), amber (#F9A825 / #FFF8E1),
  green (#43A047 / #E8F5E9), purple (#9C27B0 / #F3E5F5)
- Flow arrows: thick (stroke-width="5–6"), stroke-linecap="round"
- Typography: font-family="Inter,Arial,sans-serif"; headers bold, body regular
- Visual elements OVER text: use actual rectangles for grids/blocks/pages,
  use filled polygons for triangles/attention shapes, use bars for metrics
- Minimal text per element; let shapes carry the meaning
- Bottom footer bar: light grey (#F5F5F5), 38–62px, slide number + site URL
- NO external images, NO filters, NO blur — clean flat shapes only
"""


def generate_overview_svg(brief: dict[str, Any], payload: dict[str, Any], references: str) -> str:
    system = f"""\
You are a technical SVG infographic creator producing ByteByteGo-style explainer graphics.
{SVG_STYLE_GUIDE}
Return ONLY the raw SVG code. No markdown, no explanation, no code fences.
Canvas size: 1400x800 viewBox.
The graphic should be a two-panel overview (left panel + right panel) showing the key concepts.
Use real visual shapes — grids, bars, flow arrows — not just text boxes.
"""
    user = f"""\
Topic: {brief.get("refined_topic", "")}
Why it matters: {brief.get("why_this_matters", "")}
Key questions answered: {json.dumps(brief.get("key_questions", []))}

Post title: {payload.get("title", "")}
Post body (first 800 chars): {payload.get("post_body", "")[:800]}

References:
{references or "(none)"}

Generate a two-panel 1400x800 SVG overview infographic in ByteByteGo style.
"""
    return call_claude_text(system, user, max_tokens=6000)


def generate_slide_svgs(brief: dict[str, Any], payload: dict[str, Any], references: str) -> list[str]:
    system = f"""\
You are a technical SVG slide creator producing ByteByteGo-style explainer slides.
{SVG_STYLE_GUIDE}
Canvas size per slide: 1200x1500 viewBox.
Each slide must cover ONE concept clearly with visual shapes (grids, bars, diagrams).
Return a JSON array of exactly 4 SVG strings: [{{"svg": "<svg>...</svg>"}}, ...]
No extra keys. Each svg value is raw SVG text.
"""
    user = f"""\
Topic: {brief.get("refined_topic", "")}
Key questions: {json.dumps(brief.get("key_questions", []))}
Post body (first 1200 chars): {payload.get("post_body", "")[:1200]}

Generate 4 slides covering:
1. Overview / big picture (what are the two papers and what problem they solve)
2. First paper / mechanism A in detail (with visual diagram)
3. Second paper / mechanism B in detail (with visual diagram)
4. Key takeaways + accuracy/quality signal (with visual)

Each slide: dark navy header, colored section cards, real SVG shapes for diagrams.
"""
    raw = call_claude_text(system, user, max_tokens=10000)
    # strip markdown fences if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        items = json.loads(raw)
        return [item["svg"] for item in items]
    except Exception as exc:
        print(f"Warning: could not parse slide SVGs from Claude response: {exc}")
        return []


def write_slides_html(slug: str, num_slides: int) -> Path:
    SLIDES_HTML_DIR.mkdir(parents=True, exist_ok=True)
    slide_figures = "\n".join(
        f'  <figure class="slide"><img src="../images/slides/{slug}-0{i+1}.svg" alt="Slide {i+1}"></figure>'
        for i in range(num_slides)
    )
    html = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{slug} slides</title>
  <style>
    body {{ font-family: Inter, sans-serif; background: #f5f5f5; margin: 0; padding: 40px 60px; }}
    h1 {{ font-size: 28px; margin-bottom: 8px; }}
    .meta {{ font-size: 14px; color: #555; margin-bottom: 32px; }}
    .slide {{ margin: 0 0 40px; page-break-after: always; }}
    .slide img {{ width: 100%; max-width: 900px; display: block; border: 1px solid #ddd; border-radius: 8px; }}
    @media print {{ body {{ padding: 0; }} .slide {{ margin: 0; }} }}
  </style>
</head>
<body>
  <h1>{slug} — slide deck</h1>
  <p class="meta">
    PDF: <a href="./{slug}.pdf">./{slug}.pdf</a> ·
    Post: <a href="../../blog/{slug}/">blog/{slug}/</a>
  </p>
  <div class="slides">
{slide_figures}
  </div>
</body>
</html>
"""
    path = SLIDES_HTML_DIR / f"{slug}.html"
    path.write_text(html)
    return path


def generate_pdf_from_html(html_path: Path) -> Path | None:
    pdf_path = html_path.with_suffix(".pdf")
    chrome_candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser",
        shutil.which("google-chrome") or "",
        shutil.which("chromium") or "",
    ]
    chrome = next((c for c in chrome_candidates if c and Path(c).exists()), None)
    if not chrome:
        print("Warning: Chrome not found. Skipping PDF generation.")
        return None
    try:
        result = subprocess.run(
            [
                chrome,
                "--headless",
                "--disable-gpu",
                f"--print-to-pdf={pdf_path}",
                "--print-to-pdf-no-header",
                "--no-margins",
                f"file://{html_path.resolve()}",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            return pdf_path
        print(f"Warning: PDF generation failed: {result.stderr}")
    except Exception as exc:
        print(f"Warning: PDF generation failed: {exc}")
    return None


def render_mermaid(mermaid_code: str, output_path: Path) -> bool:
    temp_mmd = output_path.with_suffix(".mmd")
    temp_config = output_path.parent / "mermaid-config.json"
    mmdc_bin = resolve_mmdc_binary()

    temp_mmd.write_text(mermaid_code)
    temp_config.write_text(json.dumps(MERMAID_CONFIG))
    try:
        result = subprocess.run(
            [
                mmdc_bin,
                "-i",
                str(temp_mmd),
                "-o",
                str(output_path),
                "-c",
                str(temp_config),
                "-w",
                "1200",
                "-b",
                "white",
                "--scale",
                "2",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            print(f"Warning: mermaid-cli failed: {result.stderr}")
            print("Falling back to .mmd source only.")
            return False
        return True
    except FileNotFoundError:
        print("Warning: mmdc not found. Falling back to .mmd source only.")
        return False
    finally:
        temp_mmd.unlink(missing_ok=True)
        temp_config.unlink(missing_ok=True)


def build_sources_md(urls: list[str]) -> str:
    if not urls:
        return ""
    lines = ["## Sources", ""]
    lines.extend([f"- {url}" for url in urls])
    return "\n".join(lines)


def write_post(
    payload: dict[str, Any],
    slug: str,
    section: str,
    diagram_rendered: bool,
    reference_urls: list[str],
) -> Path:
    date = datetime.now().strftime("%Y-%m-%d")
    section_dir = CONTENT_DIR / section
    section_dir.mkdir(parents=True, exist_ok=True)
    post_path = section_dir / f"{slug}.md"
    show_toc = "true" if section == "blog" else "false"

    if diagram_rendered:
        diagram_md = f'![{payload["diagram_caption"]}](/images/vizpub/{slug}.png)\n*{payload["diagram_caption"]}*'
    else:
        diagram_md = f'```mermaid\n{payload["mermaid"]}\n```\n*{payload["diagram_caption"]}*'

    frontmatter = dedent(
        f"""\
        ---
        title: "{payload['title']}"
        date: {date}
        description: "{payload['description']}"
        tags: {json.dumps(payload['tags'])}
        summary: "{payload['description']}"
        ShowToc: {show_toc}
        draft: true
        ---
        """
    )

    sources_md = build_sources_md(reference_urls)
    body_parts = [
        frontmatter.strip(),
        "",
        diagram_md,
        "",
        payload["post_body"].strip(),
    ]
    if sources_md:
        body_parts.extend(["", "---", "", sources_md])
    body_parts.extend(
        [
            "",
            "---",
            "",
            "*Generated with vizpub, then reviewed and edited for accuracy. Review every claim before publishing.*",
            "",
        ]
    )
    post_path.write_text("\n".join(body_parts))
    return post_path


def write_learning_summary(payload: dict[str, Any], brief: dict[str, Any], slug: str) -> Path:
    summary_dir = DRAFTS_DIR / "learning"
    summary_dir.mkdir(parents=True, exist_ok=True)
    summary_path = summary_dir / f"{slug}.md"
    bullets = "\n".join(f"- {item}" for item in payload["learning_summary"])

    summary = dedent(
        f"""\
        # Learning Summary — {payload['title']}

        ## Refined angle
        - Topic: {brief.get('refined_topic', '')}
        - Why this matters: {brief.get('why_this_matters', '')}
        - Teaching goal: {brief.get('teaching_goal', '')}

        ## Feynman check
        {bullets}

        ## Review checklist
        1. Can you explain each bullet without looking anything up?
        2. Does the diagram reflect the real mechanism, not just a pretty abstraction?
        3. What would a strong infra / research engineer object to?
        4. What is the single most useful non-obvious insight?

        ## Mermaid source
        ```mermaid
        {payload['mermaid']}
        ```
        """
    )
    summary_path.write_text(summary)
    return summary_path


def write_linkedin_draft(payload: dict[str, Any], slug: str, post_url: str) -> Path:
    out_dir = DRAFTS_DIR / "linkedin"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{slug}.md"
    text = dedent(
        f"""\
        # LinkedIn Draft
        ## {payload['title']}

        {payload['linkedin_text']}

        ---

        ### First comment
        Full writeup with diagram: {post_url}

        ### Checklist
        - [ ] Upload diagram as native image or PDF carousel
        - [ ] Keep links out of body text
        - [ ] Post Tue–Thu, 8–10 AM EST
        """
    )
    path.write_text(text)
    return path


def write_x_draft(payload: dict[str, Any], slug: str, post_url: str) -> Path:
    out_dir = DRAFTS_DIR / "x"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{slug}.md"
    thread = "\n\n".join(f"**Tweet {idx + 1}:**\n{tweet}" for idx, tweet in enumerate(payload["x_thread"]))
    text = dedent(
        f"""\
        # X Thread Draft
        ## {payload['title']}

        {thread}

        ---

        ### Final link
        {post_url}
        """
    )
    path.write_text(text)
    return path


def write_hn_draft(payload: dict[str, Any], slug: str, post_url: str) -> Path:
    out_dir = DRAFTS_DIR / "hn"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{slug}.md"
    text = dedent(
        f"""\
        # Hacker News Draft

        ## Title
        {payload['hn_title']}

        ## URL
        {post_url}

        ## Submission text / self-post body
        {payload['hn_text']}

        ## Reminder
        - Use only for strong deep dives worth HN attention
        - Keep the title factual, not hypey
        """
    )
    path.write_text(text)
    return path


def print_summary(
    post_path: Path,
    diagram_path: Path,
    diagram_rendered: bool,
    learning_path: Path,
    outputs: dict[str, Path],
) -> None:
    print("\n" + "=" * 64)
    print("✅ VIZPUB COMPLETE")
    print("=" * 64)
    print(f"📝 Post:     {post_path}")
    print(f"🧠 Learning: {learning_path}")
    print(f"📊 Diagram:  {diagram_path if diagram_rendered else diagram_path.with_suffix('.mmd')}")
    for label, path in outputs.items():
        print(f"{label:>11}: {path}")
    print("\nNext steps:")
    print("1. Review the learning summary and diagram first")
    print("2. Edit the draft until every claim is defendable")
    print("3. Set draft: false when ready")
    print("4. git add . && git commit && git push")
    print("5. Post manual social / HN only when the piece is strong enough")


def build_post_url(site_url: str, section: str, slug: str) -> str:
    return f"{site_url.rstrip('/')}/{section}/{slug}/"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="VIZPUB v2 — interactive publisher-manager workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=dedent(
            """\
            Examples:
              .venv/bin/python scripts/vizpub.py --topic "How KV-cache paging works in vLLM"
              .venv/bin/python scripts/vizpub.py --topic "FSDP sharding strategies" --section blog --target hn
              .venv/bin/python scripts/vizpub.py --topic "PagedAttention" --paper https://arxiv.org/abs/2309.06180 --paper https://example.com/post
            """
        ),
    )
    parser.add_argument("--topic", help="Topic to publish")
    parser.add_argument("--paper", action="append", help="Paper / reference URL (repeatable, comma-separated also supported)")
    parser.add_argument("--focus", help="Specific angle to focus on")
    parser.add_argument("--slug", help="Custom slug")
    parser.add_argument("--section", default="experiments", help="blog, lab-notes, experiments, or notes")
    parser.add_argument("--target", action="append", help="Promotion targets: linkedin,x,hn")
    parser.add_argument("--site-url", default=DEFAULT_SITE_URL, help="Base site URL")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode")
    args = parser.parse_args()

    interactive = args.interactive or (not args.topic and not args.paper)
    if interactive:
        config = prompt_interactively()
    else:
        if not args.topic:
            print("Error: --topic is required unless using --interactive")
            sys.exit(1)
        config = {
            "topic": args.topic,
            "focus": args.focus or "",
            "section": normalize_section(args.section),
            "papers": split_csv_values(args.paper),
            "targets": parse_targets(args.target),
            "site_url": args.site_url,
            "slug": args.slug or "",
        }

    require_api_key()
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

    references = build_reference_context(config["papers"])

    print("🧭 Refining publishing brief...")
    brief = refine_brief(
        topic=config["topic"],
        focus=config["focus"],
        section=config["section"],
        targets=config["targets"],
        references=references,
    )

    section = config["section"]
    if not interactive:
        section = normalize_section(config["section"])
    else:
        section = normalize_section(config["section"])

    slug = config["slug"] or brief.get("suggested_slug") or slugify(brief.get("refined_topic", config["topic"]))
    section = normalize_section(section)
    post_url = build_post_url(config["site_url"], section, slug)

    print("🤖 Generating content package...")
    payload = generate_content_package(brief, section, config["targets"], references)
    payload = normalize_payload(payload, config["targets"])

    # ── Visual assets ──────────────────────────────────────────────
    print("🎨 Generating ByteByteGo-style SVG overview...")
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    overview_svg_path = STATIC_DIR / f"{slug}.svg"
    try:
        overview_svg = generate_overview_svg(brief, payload, references)
        overview_svg_path.write_text(overview_svg)
        print(f"   ✅ Overview SVG: {overview_svg_path}")
    except Exception as exc:
        print(f"   ⚠️  Overview SVG failed: {exc}")

    print("🎨 Generating ByteByteGo-style slide deck (4 slides)...")
    SLIDES_DIR.mkdir(parents=True, exist_ok=True)
    slide_svgs: list[str] = []
    try:
        slide_svgs = generate_slide_svgs(brief, payload, references)
        for i, svg_code in enumerate(slide_svgs):
            slide_path = SLIDES_DIR / f"{slug}-0{i+1}.svg"
            slide_path.write_text(svg_code)
        print(f"   ✅ {len(slide_svgs)} slides written to {SLIDES_DIR}")
    except Exception as exc:
        print(f"   ⚠️  Slide SVGs failed: {exc}")

    # HTML wrapper + PDF
    slides_html_path: Path | None = None
    slides_pdf_path: Path | None = None
    if slide_svgs:
        slides_html_path = write_slides_html(slug, len(slide_svgs))
        print(f"   ✅ Slides HTML: {slides_html_path}")
        print("   📄 Generating PDF...")
        slides_pdf_path = generate_pdf_from_html(slides_html_path)
        if slides_pdf_path:
            print(f"   ✅ PDF: {slides_pdf_path}")

    # ── Mermaid fallback diagram ────────────────────────────────────
    mermaid_source_path = STATIC_DIR / f"{slug}.mmd"
    diagram_path = STATIC_DIR / f"{slug}.png"
    mermaid_source_path.write_text(payload["mermaid"])
    diagram_rendered = render_mermaid(payload["mermaid"], diagram_path)

    # ── Post and social drafts ─────────────────────────────────────
    post_path = write_post(payload, slug, section, diagram_rendered, config["papers"])
    learning_path = write_learning_summary(payload, brief, slug)

    outputs: dict[str, Path] = {}
    if "linkedin" in config["targets"]:
        outputs["LinkedIn"] = write_linkedin_draft(payload, slug, post_url)
    if "x" in config["targets"]:
        outputs["X thread"] = write_x_draft(payload, slug, post_url)
    if "hn" in config["targets"]:
        outputs["HN draft"] = write_hn_draft(payload, slug, post_url)

    if slides_html_path:
        outputs["Slides HTML"] = slides_html_path
    if slides_pdf_path:
        outputs["Slides PDF"] = slides_pdf_path

    print_summary(post_path, diagram_path, diagram_rendered, learning_path, outputs)


if __name__ == "__main__":
    main()
