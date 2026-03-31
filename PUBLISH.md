# Publishing Workflow

## Is it automated?

**Generation is automated. Posting is manual.**

vizpub.py does the heavy lifting: reads papers, calls Claude, writes the blog post, generates ByteByteGo-style SVG diagrams + slides, and writes your LinkedIn/X/HN drafts. You then review everything, approve it, and post manually. You always control the final publish step.

---

## Step 1 — Generate content from a topic + paper links

```bash
cd ~/projects/zhanyl-tech.github.io
source .venv/bin/activate    # or: .venv/bin/python

.venv/bin/python scripts/vizpub.py \
  --topic "How vLLM schedules KV cache memory" \
  --section blog \
  --paper https://arxiv.org/abs/2309.06180 \
  --paper https://arxiv.org/abs/2502.14866
```

What it outputs:
- `content/blog/YYYY-MM-DD-your-slug.md` — blog post draft (set `draft: true`)
- `static/images/vizpub/your-slug.svg` — ByteByteGo-style overview infographic
- `static/images/slides/your-slug-01.svg` through `04.svg` — 4 visual slides
- `static/slides/your-slug.html` — slide viewer page
- `static/slides/your-slug.pdf` — PDF ready for LinkedIn document upload
- `cope-drafts/linkedin/your-slug.md` — LinkedIn post draft
- `cope-drafts/x/your-slug.md` — X thread draft
- `cope-drafts/hn/your-slug.md` — HN submission (optional)

---

## Step 2 — Review on the live site

1. In the markdown file, change `draft: true` → `draft: false`
2. Build and push:
   ```bash
   hugo --minify
   git add .
   git commit -m "add: your-post-title"
   git push
   ```
3. Wait ~2 minutes for GitHub Actions to deploy
4. Review at `https://zhanyl-tech.github.io/blog/your-slug/`
5. Review slides at `https://zhanyl-tech.github.io/slides/your-slug.html`

---

## Step 3 — Post on LinkedIn

LinkedIn does not have an API for regular users. You post manually:

1. Open `cope-drafts/linkedin/your-slug.md` — copy the post text
2. Go to LinkedIn → Start a post
3. Paste the text
4. Click the document icon (📄) → upload `static/slides/your-slug.pdf`
   - This shows up as a scrollable carousel in the feed — ByteByteGo style
5. In the **first comment** (not the post body), add the link to your article:
   `https://zhanyl-tech.github.io/blog/your-slug/`
6. Best time: Tuesday–Thursday, 8–10 AM EST

> **Why no link in the body?** LinkedIn's algorithm buries posts with external links in the body. The first comment is the workaround everyone uses.

---

## Step 4 — Post on X (Twitter)

X does not allow automated posting without an approved developer app. You post manually:

1. Open `cope-drafts/x/your-slug.md` — copy Tweet 1
2. Go to X → New post → paste Tweet 1 → post it
3. Reply to your own tweet with Tweet 2, 3, 4... (this is the thread)
4. On the last tweet, add: `https://zhanyl-tech.github.io/blog/your-slug/`

> **Tip:** Attach the slide 1 SVG/PNG as an image on Tweet 1 for higher engagement.
> The overview SVG is at `static/images/vizpub/your-slug.svg`.

---

## Step 5 — Hacker News (for strong deep dives only)

1. Open `cope-drafts/hn/your-slug.md` — use the title and URL
2. Go to `https://news.ycombinator.com/submit`
3. Paste title and URL — no body text needed for link submissions
4. Best time: weekday morning 8–10 AM EST

---

## Quick re-run a post through COPE only

If you already have a blog post and just want fresh social drafts:

```bash
bash scripts/cope.sh content/blog/your-post.md --linkedin --x --hn
```

---

## Full workflow in one view

```
Give topic + paper links
        ↓
  vizpub.py
        ↓
  ┌─────────────────────────────────────────────┐
  │  blog post draft (draft: true)              │
  │  SVG overview infographic                   │
  │  4 SVG slides + HTML viewer + PDF           │
  │  LinkedIn draft (text + PDF ready)          │
  │  X thread draft                             │
  │  HN submission draft                        │
  └─────────────────────────────────────────────┘
        ↓
  Review + edit
        ↓
  draft: false → git push → GitHub Pages (2 min)
        ↓
  Manual post:
    LinkedIn → upload PDF as document post
    X        → paste thread manually
    HN       → submit link
```
