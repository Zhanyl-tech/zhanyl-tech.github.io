# SITE PLAYBOOK — Full Picture

> Everything in one place: what's built, what goes where, and how to publish.

---

## 1. TECH STACK AT A GLANCE

```
Framework:    Hugo v0.159 (extended)
Theme:        PaperMod (git submodule → themes/PaperMod/)
Config:       hugo.yaml (root)
Hosting:      GitHub Pages
Deploy:       GitHub Actions (.github/workflows/deploy.yml)
              push to main → auto-build → live in ~2 min
URL:          https://zhanyl-tech.github.io
```

---

## 2. FULL DIRECTORY MAP

```
zhanyl-tech.github.io/
│
├── hugo.yaml                          ← Site config: theme, menu, social links, profileMode
├── .gitignore                         ← Excludes: public/, cope-drafts/, .hugo_build.lock
├── .gitmodules                        ← PaperMod submodule reference
│
├── .github/
│   └── workflows/
│       └── deploy.yml                 ← GitHub Actions: push → hugo build → Pages deploy
│
├── content/                           ← ALL site content lives here (markdown files)
│   │
│   ├── blog/
│   │   └── _index.md                  ← Section description (shown on /blog/)
│   │   └── YYYY-MM-DD-post-title.md   ← ADD: deep dive posts (2000-4000 words)
│   │
│   ├── experiments/
│   │   └── _index.md                  ← Section description (shown on /experiments/)
│   │   └── YYYY-MM-DD-exp-title.md    ← ADD: lab notebook posts (500-1500 words)
│   │
│   ├── projects/
│   │   └── _index.md                  ← Section description
│   │   ├── agentic-ml-inference-infrastructure.md   ← P1 (deadline Aug 2026)
│   │   ├── distributed-training-platform.md         ← P2 (deadline Aug 2026)
│   │   └── gpu-volatility-surface.md                ← P3 (deadline Nov 2026)
│   │
│   ├── notes/
│   │   └── _index.md                  ← Section description
│   │   └── YYYY-MM-DD-note-title.md   ← ADD: TILs, paper summaries (100-500 words)
│   │
│   ├── about.md                       ← Bio, focus, chess/poker line, resume link
│   ├── reading.md                     ← Curated book list (update quarterly)
│   └── search.md                      ← PaperMod search page (no edits needed)
│
├── static/                            ← Files served as-is (no Hugo processing)
│   ├── resume.pdf                     ← REPLACE with your real PDF (linked from /about)
│   └── images/
│       ├── avatar.jpg                 ← ADD: your profile photo
│       └── vizpub/                    ← VIZPUB drops rendered diagram PNGs here
│           └── [slug].png
│
├── themes/
│   └── PaperMod/                      ← Git submodule — DO NOT edit files here
│
├── scripts/                           ← Publishing automation (run locally, never deployed)
│   ├── cope.sh                        ← Generates LinkedIn + X drafts from a post
│   └── vizpub.py                      ← Full pipeline: topic → diagram + post + social drafts
│
├── cope-drafts/                       ← GITIGNORED — local draft files only
│   ├── linkedin/[slug].md             ← LinkedIn post draft
│   ├── x/[slug].md                    ← X thread draft
│   └── learning/[slug].md             ← Feynman learning summary (vizpub only)
│
└── public/                            ← GITIGNORED — Hugo build output (auto-generated)
```

---

## 3. SITE URL MAP

```
https://zhanyl-tech.github.io/              → Homepage (profileMode: bio + latest posts)
https://zhanyl-tech.github.io/blog/         → Deep dives (2000-4000 words)
https://zhanyl-tech.github.io/experiments/  → Lab notebook (500-1500 words)
https://zhanyl-tech.github.io/projects/     → 3 portfolio projects (permanent pages)
https://zhanyl-tech.github.io/notes/        → Quick TILs (100-500 words)
https://zhanyl-tech.github.io/reading/      → Book list (single page)
https://zhanyl-tech.github.io/about/        → Bio + resume download + contact
https://zhanyl-tech.github.io/search/       → Full-text search
https://zhanyl-tech.github.io/resume.pdf    → Direct PDF download
```

---

## 4. CONTENT DECISION TREE

```
Got something to publish?
│
├── Is it a deep technical analysis, architecture writeup, or system design post?
│   Length: 2000-4000 words. Would a staff engineer share this?
│   → content/blog/YYYY-MM-DD-title.md          ShowToc: true
│
├── Did you deploy a tool, run a benchmark, or document what you found first?
│   Length: 500-1500 words. Raw is fine. Terminal screenshots welcome.
│   → content/experiments/YYYY-MM-DD-title.md   ShowToc: false
│
├── Did you read a paper, learn a concept, or have a quick insight worth logging?
│   Length: 100-500 words. "Note to self" energy.
│   → content/notes/YYYY-MM-DD-title.md         ShowToc: false
│
├── Did you hit a milestone on P1, P2, or P3?
│   → Edit the relevant content/projects/ file. Add milestone, update benchmarks table.
│
└── Did you finish a book worth recommending?
    → Edit content/reading.md (update quarterly)
```

---

## 5. TWO PUBLISHING PATHS

### PATH A — vizpub.py (Visual-First, Recommended for Experiments + Blog)

```
You have a topic or paper
        │
        ▼
python scripts/vizpub.py --topic "How KV-cache paging works in vLLM"
        │
        │   Claude API call (single call, all outputs at once)
        │
        ├──▶ static/images/vizpub/[slug].png        ← Mermaid diagram (ByteByteGo style)
        ├──▶ content/experiments/[slug].md           ← Blog post (draft: true)
        ├──▶ cope-drafts/linkedin/[slug].md          ← LinkedIn post draft
        ├──▶ cope-drafts/x/[slug].md                 ← X thread draft
        └──▶ cope-drafts/learning/[slug].md          ← Feynman learning summary
        │
        ▼
YOU REVIEW (this is the learning step — don't skip it)
   1. Read learning summary → can you explain each bullet simply?
   2. Check diagram at mermaid.live → fix any inaccuracies
   3. Edit blog post → add YOUR insight (what production experience adds)
   4. Remove anything you can't personally defend
        │
        ▼
Set draft: false in the post frontmatter
        │
        ▼
git add . && git commit -m "Experiment: [title]" && git push
        │
        ▼
GitHub Actions builds (~2 min) → site live
        │
        ▼
Run cope.sh to generate/refresh social drafts (or use vizpub drafts directly)
        │
        ▼
POST SOCIAL (manually)
   LinkedIn: Tue–Thu 8–10 AM EST  (native image + text, link in first comment)
   X thread: Wednesday 8–10 AM EST (image on tweet 1)
   HN:       Deep dives only → news.ycombinator.com/submit
```

### PATH B — cope.sh (Social Drafts Only, for Posts Written Manually)

```
You already wrote a post manually
        │
        ▼
./scripts/cope.sh content/blog/your-post.md
        │
        ├──▶ cope-drafts/linkedin/[slug].md
        └──▶ cope-drafts/x/[slug].md
        │
        ▼
Edit drafts → post manually (same schedule as above)
```

---

## 6. VIZPUB COMMAND REFERENCE

```bash
# Setup (one-time)
pip install anthropic requests
npm install -g @mermaid-js/mermaid-cli
export ANTHROPIC_API_KEY=sk-ant-...        # add to ~/.zshrc to persist

# From a topic → /experiments post (default)
python scripts/vizpub.py --topic "How KV-cache paging works in vLLM"

# From a paper URL (auto-fetches abstract)
python scripts/vizpub.py \
  --paper "https://arxiv.org/abs/2309.06180" \
  --focus "PagedAttention memory management"

# Force /blog section (for longer deep dives)
python scripts/vizpub.py --topic "FSDP vs DDP sharding" --section blog

# Custom slug
python scripts/vizpub.py --topic "FlashAttention memory" --slug "flashattention-memory"

# What it generates every time:
#   static/images/vizpub/[slug].png          ← diagram PNG
#   static/images/vizpub/[slug].mmd          ← Mermaid source (if PNG failed)
#   content/experiments/[slug].md            ← post (draft: true)
#   cope-drafts/linkedin/[slug].md
#   cope-drafts/x/[slug].md
#   cope-drafts/learning/[slug].md
```

---

## 7. NEW POST FRONTMATTER TEMPLATES

### /blog post
```yaml
---
title: "GPU-Accelerated Volatility Surface Calibration: From Dupire to CUDA Kernel"
date: 2026-XX-XX
description: "One-line description for SEO and social sharing"
tags: [cuda, gpu, quantitative-finance, derivatives, hpc]
summary: "Same as description"
ShowToc: true
cover:
  image: "/images/vizpub/your-slug.png"
  alt: "Diagram caption"
---
```

### /experiments post
```yaml
---
title: "vLLM vs TensorRT-LLM: Throughput on Llama-3 70B"
date: 2026-XX-XX
description: "One-line description"
tags: [vllm, tensorrt, inference, benchmark, llm]
summary: "Same as description"
ShowToc: false
---
```

### /notes post
```yaml
---
title: "Paper: PagedAttention — The KV Cache Insight Nobody Explains Clearly"
date: 2026-XX-XX
description: "One-line description"
tags: [paper, inference, kv-cache]
summary: "Same as description"
ShowToc: false
---
```

---

## 8. DEPLOY PIPELINE (Automatic)

```
Your machine                    GitHub                      GitHub Pages
─────────────                   ──────                      ────────────
git push origin main    ──▶     Receives push          
                                      │
                                      ▼
                                Actions triggers
                                deploy.yml
                                      │
                                      ├── Install Hugo v0.159 (extended)
                                      ├── Checkout repo + submodules (PaperMod)
                                      ├── hugo --minify --baseURL
                                      └── Upload public/ artifact
                                              │
                                              ▼
                                      deploy-pages action  ──▶  zhanyl-tech.github.io
                                                                 (~2 min total)
```

**Required GitHub setting (one-time):**
`Settings → Pages → Source → GitHub Actions` ← change from "Deploy from branch"

---

## 9. WEEKLY WORKFLOW

### Now → May 10 (GPA Protection — ~1.5 hrs/week)

```
Sat  30 min  Run one experiment (deploy a tool, run a benchmark)
Sun  30 min  Write /experiments post from Saturday's results
     15 min  Run vizpub.py OR cope.sh → edit social drafts
     15 min  Post LinkedIn + X
```

### May 10+ (~5-6 hrs/week)

```
Sat AM  2-3 hrs  Write or continue /blog deep dive
Sat PM    1 hr   Run experiment → document results
Sun AM    1 hr   Finalize /experiments post
Sun PM   30 min  Run vizpub/cope → edit social drafts
         30 min  Post LinkedIn + X + submit HN (deep dives only)
Monthly   1 hr   Newsletter digest (start September 2026)
```

---

## 10. WHAT YOU NEED TO PERSONALIZE

Open these files and replace placeholders:

**`hugo.yaml`** — update these values:
```yaml
socialIcons:
  - url: "https://github.com/YOUR_REAL_USERNAME"
  - url: "https://linkedin.com/in/YOUR_REAL_PROFILE"
  - url: "https://twitter.com/YOUR_REAL_HANDLE"
  - url: "mailto:YOUR_REAL@EMAIL.COM"
```

**`content/about.md`** — update:
```markdown
- [GitHub](https://github.com/YOUR_USERNAME)
- [Twitter/X](https://twitter.com/YOUR_USERNAME)
- [LinkedIn](https://linkedin.com/in/YOUR_USERNAME)
- Email: [YOUR@EMAIL.COM](mailto:YOUR@EMAIL.COM)
```

**`static/resume.pdf`** — replace the placeholder with your real PDF

**`static/images/avatar.jpg`** — add your profile photo (used on homepage)

---

## 11. SCRIPTS QUICK REFERENCE

```bash
# Generate diagram + post + social drafts from a topic (VIZPUB)
python scripts/vizpub.py --topic "YOUR TOPIC HERE"

# Generate social drafts only from an existing post (COPE)
./scripts/cope.sh content/experiments/your-post.md

# Test site locally (runs at http://localhost:1313)
hugo server -D

# Build site manually (output → public/)
hugo --minify

# Add a new post manually
hugo new experiments/2026-04-01-my-experiment.md

# Update PaperMod theme
git submodule update --remote themes/PaperMod
```
