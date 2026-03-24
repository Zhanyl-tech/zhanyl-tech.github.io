#!/usr/bin/env python3
"""
VIZPUB — Visual-First Publishing Pipeline
==========================================
One command → diagram + blog post + social drafts.

Usage:
  # From a topic
  python scripts/vizpub.py --topic "How KV-cache paging works in vLLM"

  # From a paper URL
  python scripts/vizpub.py --paper "https://arxiv.org/abs/2309.06180" --focus "PagedAttention memory management"

  # From a topic with custom slug
  python scripts/vizpub.py --topic "FlashAttention vs standard attention" --slug "flashattention-comparison"

  # Specify section (experiments is default)
  python scripts/vizpub.py --topic "FSDP sharding strategies" --section blog

What it generates:
  1. Mermaid diagram → rendered to PNG (ByteByteGo style)
  2. /experiments (or /blog) markdown post with diagram embedded
  3. LinkedIn draft
  4. X/Twitter thread draft
  5. Learning summary (Feynman-style — forces YOUR understanding)

Requirements:
  pip install anthropic requests
  npm install -g @mermaid-js/mermaid-cli   # for diagram rendering
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from textwrap import dedent

try:
    import anthropic
except ImportError:
    print("Install anthropic: pip install anthropic")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)


# ─── CONFIG ──────────────────────────────────────────────────────────
HUGO_ROOT = Path(__file__).parent.parent  # scripts/ is one level down from root
CONTENT_DIR = HUGO_ROOT / "content"
STATIC_DIR = HUGO_ROOT / "static" / "images" / "vizpub"
DRAFTS_DIR = HUGO_ROOT / "cope-drafts"
MODEL = "claude-sonnet-4-20250514"

# Mermaid config — ByteByteGo-inspired clean style
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
        "fontFamily": "Inter, system-ui, sans-serif"
    }
}


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text[:60].rstrip('-')


def fetch_paper_abstract(url: str) -> str:
    if "arxiv.org" in url:
        arxiv_url = url.replace("/pdf/", "/abs/").rstrip(".pdf")
        try:
            resp = requests.get(arxiv_url, timeout=10)
            text = resp.text
            title_match = re.search(r'<meta name="citation_title" content="([^"]+)"', text)
            abstract_match = re.search(
                r'<blockquote class="abstract[^"]*">\s*<span class="descriptor">Abstract:</span>\s*(.*?)</blockquote>',
                text, re.DOTALL
            )
            title = title_match.group(1) if title_match else "Unknown"
            abstract = abstract_match.group(1).strip() if abstract_match else ""
            abstract = re.sub(r'<[^>]+>', '', abstract).strip()
            return f"Paper: {title}\n\nAbstract: {abstract}\n\nURL: {url}"
        except Exception as e:
            print(f"Warning: Could not fetch paper: {e}")
            return f"Paper URL: {url}"
    else:
        return f"Paper/Reference URL: {url}"


def call_claude(system_prompt: str, user_prompt: str) -> str:
    client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var
    message = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )
    return message.content[0].text


def generate_all_content(topic: str, paper_context: str = "", focus: str = "") -> dict:
    system = dedent("""\
    You are a technical content generator for a senior HPC/ML infrastructure engineer's
    blog. You create ByteByteGo-style visual explanations of ML systems concepts.

    Your output must be valid JSON with exactly these keys:
    - title: Post title (staff-engineer voice, not student voice)
    - description: One-line description for frontmatter
    - tags: Array of relevant tags
    - mermaid: Mermaid diagram code (flowchart TD or LR format, clean and readable)
    - blog_body: Markdown blog post body (500-1500 words for experiments, longer for blog)
    - linkedin_text: LinkedIn native post text (3-5 lines + key insights as arrows →)
    - x_thread: Array of 3-5 tweets for an X thread
    - learning_summary: 3-5 bullet Feynman-style "explain it simply" summary
    - diagram_caption: One-line caption for the diagram

    CRITICAL RULES for the Mermaid diagram:
    - Use flowchart TD (top-down) or LR (left-right) — pick whichever fits the concept
    - Maximum 8-12 nodes. Simplicity is key. ByteByteGo diagrams are CLEAN.
    - Use subgraphs to group related components
    - Node labels must be SHORT (3-5 words max)
    - Use different node shapes: [] for process, {} for decision, () for data, [( )] for database
    - Add descriptive edge labels where they clarify flow
    - Color-code with classDef: primary for main flow, secondary for side effects, highlight for key insight

    CRITICAL RULES for blog body:
    - Staff engineer voice. "Here's how this works" not "I learned that"
    - Start with the problem/context (why does this matter?)
    - Explain the mechanism (what's actually happening?)
    - Add your insight (what's non-obvious about this?)
    - End with practical implications (why should an ML infra engineer care?)

    CRITICAL RULES for LinkedIn:
    - NO external links in the text body
    - Start with a hook (surprising fact or contrarian take)
    - Use → arrows for key insights
    - End with "Full breakdown with diagrams on my blog" (link goes in first comment)
    - Include relevant hashtags

    CRITICAL RULES for X thread:
    - Tweet 1: Hook + "🧵👇"
    - Middle tweets: One insight per tweet, punchy
    - Last tweet: CTA to blog post + follow request
    - Each tweet under 280 characters

    Return ONLY valid JSON. No markdown code fences. No explanatory text outside the JSON.
    """)

    context_parts = [f"Topic: {topic}"]
    if paper_context:
        context_parts.append(f"\nPaper context:\n{paper_context}")
    if focus:
        context_parts.append(f"\nSpecific focus: {focus}")
    context_parts.append(
        "\nAuthor context: Senior HPC/cluster engineer at a quant trading firm. "
        "GT OMSCS ML specialization. CQF. Writes about GPU inference, distributed training, "
        "agentic AI infrastructure. Staff-engineer voice."
    )

    user_msg = "\n".join(context_parts)

    print("🤖 Generating content with Claude...")
    raw = call_claude(system, user_msg)

    # Strip markdown fences if present
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"Error parsing Claude response: {e}")
        print(f"Raw response:\n{raw[:500]}...")
        sys.exit(1)


def render_mermaid(mermaid_code: str, output_path: Path) -> bool:
    temp_mmd = output_path.with_suffix('.mmd')
    temp_config = output_path.parent / "mermaid-config.json"

    temp_mmd.write_text(mermaid_code)
    temp_config.write_text(json.dumps(MERMAID_CONFIG))

    try:
        result = subprocess.run(
            [
                "mmdc",
                "-i", str(temp_mmd),
                "-o", str(output_path),
                "-c", str(temp_config),
                "-w", "1200",
                "-b", "white",
                "--scale", "2"
            ],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            print(f"Warning: mermaid-cli failed: {result.stderr}")
            print("Falling back to .mmd file only. Render manually at mermaid.live")
            return False
        return True
    except FileNotFoundError:
        print("Warning: mermaid-cli (mmdc) not found.")
        print("Install: npm install -g @mermaid-js/mermaid-cli")
        print("Mermaid source saved — paste into mermaid.live to render manually.")
        return False
    finally:
        temp_mmd.unlink(missing_ok=True)
        temp_config.unlink(missing_ok=True)


def write_blog_post(content: dict, slug: str, section: str, diagram_rendered: bool) -> Path:
    date = datetime.now().strftime("%Y-%m-%d")
    section_dir = CONTENT_DIR / section
    section_dir.mkdir(parents=True, exist_ok=True)
    post_path = section_dir / f"{slug}.md"

    show_toc = "true" if section == "blog" else "false"

    if diagram_rendered:
        diagram_md = f'![{content["diagram_caption"]}](/images/vizpub/{slug}.png)\n*{content["diagram_caption"]}*'
    else:
        diagram_md = f'```mermaid\n{content["mermaid"]}\n```\n*{content["diagram_caption"]}*'

    frontmatter = dedent(f"""\
    ---
    title: "{content['title']}"
    date: {date}
    description: "{content['description']}"
    tags: {json.dumps(content['tags'])}
    summary: "{content['description']}"
    ShowToc: {show_toc}
    draft: true
    ---
    """)

    body = f"""{frontmatter}
{diagram_md}

{content['blog_body']}

---

*Generated with vizpub, then reviewed and edited for accuracy. The diagram and analysis reflect my understanding from hands-on work with these systems.*
"""

    post_path.write_text(body)
    return post_path


def write_social_drafts(content: dict, slug: str, blog_url: str) -> tuple:
    date = datetime.now().strftime("%Y-%m-%d")

    # LinkedIn
    li_dir = DRAFTS_DIR / "linkedin"
    li_dir.mkdir(parents=True, exist_ok=True)
    li_path = li_dir / f"{slug}.md"

    li_draft = dedent(f"""\
    # LinkedIn Draft — {date}
    ## {content['title']}

    ### POST TEXT (paste into LinkedIn — upload diagram as image — NO links in body)

    {content['linkedin_text']}

    ### FIRST COMMENT
    Full breakdown with architecture diagram: {blog_url}

    ### CHECKLIST
    - [ ] Upload diagram PNG as native image (NOT a link)
    - [ ] Paste post text
    - [ ] Immediately add first comment with blog link
    - [ ] Post Tuesday-Thursday 8-10 AM EST
    """)
    li_path.write_text(li_draft)

    # X / Twitter
    x_dir = DRAFTS_DIR / "x"
    x_dir.mkdir(parents=True, exist_ok=True)
    x_path = x_dir / f"{slug}.md"

    thread_text = "\n\n".join(
        f"**Tweet {i+1}:**\n{tweet}"
        for i, tweet in enumerate(content['x_thread'])
    )

    x_draft = dedent(f"""\
    # X Thread Draft — {date}
    ## {content['title']}

    ### THREAD (post as individual tweets — attach diagram to Tweet 1)

    {thread_text}

    ### CHECKLIST
    - [ ] Attach diagram PNG to first tweet
    - [ ] Post each tweet as reply to previous
    - [ ] Post Wednesday 8-10 AM EST for peak engagement
    """)
    x_path.write_text(x_draft)

    return li_path, x_path


def write_learning_summary(content: dict, slug: str) -> Path:
    summary_dir = DRAFTS_DIR / "learning"
    summary_dir.mkdir(parents=True, exist_ok=True)
    summary_path = summary_dir / f"{slug}.md"

    bullets = "\n".join(f"- {b}" for b in content['learning_summary'])
    summary = dedent(f"""\
    # Learning Summary: {content['title']}
    ## Feynman Check — Can you explain this simply?

    {bullets}

    ## Diagram Review
    Look at the generated diagram. Ask yourself:
    1. Is every node label accurate?
    2. Are the connections/arrows showing the RIGHT data flow?
    3. What's MISSING that a staff engineer would notice?
    4. What would you change based on your production experience?

    Edit the diagram and blog post until YOU are satisfied with the accuracy.
    The review process IS the learning. Don't skip it.

    ## Mermaid Source (edit at mermaid.live if needed)
    ```mermaid
    {content['mermaid']}
    ```
    """)
    summary_path.write_text(summary)
    return summary_path


def main():
    parser = argparse.ArgumentParser(
        description="VIZPUB — Visual-First Publishing Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=dedent("""\
        Examples:
          python scripts/vizpub.py --topic "How KV-cache paging works in vLLM"
          python scripts/vizpub.py --paper "https://arxiv.org/abs/2309.06180" --focus "PagedAttention"
          python scripts/vizpub.py --topic "FSDP vs DDP" --section blog --slug fsdp-vs-ddp
        """)
    )
    parser.add_argument("--topic", required=True, help="Topic to visualize and write about")
    parser.add_argument("--paper", help="Paper URL (arXiv, etc.) for additional context")
    parser.add_argument("--focus", help="Specific aspect to focus the diagram on")
    parser.add_argument("--slug", help="Custom URL slug (auto-generated from topic if omitted)")
    parser.add_argument("--section", default="experiments",
                        choices=["experiments", "blog", "notes"],
                        help="Hugo content section (default: experiments)")
    parser.add_argument("--site-url", default="https://zhanyl-tech.github.io",
                        help="Your site URL for social post links")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: Set ANTHROPIC_API_KEY environment variable")
        print("  export ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)

    slug = args.slug or slugify(args.topic)
    blog_url = f"{args.site_url}/{args.section}/{slug}/"

    # Fetch paper context if provided
    paper_context = ""
    if args.paper:
        print(f"📄 Fetching paper: {args.paper}")
        paper_context = fetch_paper_abstract(args.paper)

    # Generate all content in one Claude call
    content = generate_all_content(args.topic, paper_context, args.focus or "")

    # Ensure output dirs exist
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

    # Render Mermaid diagram
    diagram_path = STATIC_DIR / f"{slug}.png"
    mermaid_source_path = STATIC_DIR / f"{slug}.mmd"
    mermaid_source_path.write_text(content['mermaid'])
    print(f"📊 Mermaid source: {mermaid_source_path}")

    diagram_rendered = render_mermaid(content['mermaid'], diagram_path)
    if diagram_rendered:
        print(f"🖼️  Diagram PNG: {diagram_path}")

    # Write all outputs
    post_path = write_blog_post(content, slug, args.section, diagram_rendered)
    print(f"📝 Blog post: {post_path}")

    li_path, x_path = write_social_drafts(content, slug, blog_url)
    print(f"💼 LinkedIn draft: {li_path}")
    print(f"🐦 X thread draft: {x_path}")

    learn_path = write_learning_summary(content, slug)
    print(f"🧠 Learning summary: {learn_path}")

    print("\n" + "=" * 60)
    print("✅ VIZPUB COMPLETE")
    print("=" * 60)
    print(f"\n📊 Diagram:  {diagram_path if diagram_rendered else mermaid_source_path}")
    print(f"📝 Post:     {post_path} (draft: true — review before publishing)")
    print(f"💼 LinkedIn: {li_path}")
    print(f"🐦 X Thread: {x_path}")
    print(f"🧠 Learning: {learn_path}")
    print(f"\n🔍 NEXT STEPS:")
    print(f"   1. Review {learn_path}")
    print(f"      → Can you explain each bullet simply? Edit until accurate.")
    print(f"   2. Review diagram — fix any inaccuracies at mermaid.live")
    print(f"   3. Add your personal insight to {post_path}")
    print(f"      → What surprised you? What does your production experience add?")
    print(f"   4. Set draft: false → git add → git commit → git push")
    print(f"   5. Post social: LinkedIn (Tue-Thu AM) → X (Wed AM)")
    if not diagram_rendered:
        print(f"\n⚠️  Diagram not auto-rendered.")
        print(f"   Paste {mermaid_source_path} into https://mermaid.live")
        print(f"   Export as PNG (2x scale) → save to {diagram_path}")


if __name__ == "__main__":
    main()
