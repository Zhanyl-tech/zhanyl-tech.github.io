#!/bin/bash
# COPE Workflow: Create Once, Publish Everywhere
# Usage: ./scripts/cope.sh content/blog/my-post.md [--hn]

set -e

POST_PATH="$1"
shift || true

GENERATE_HN=0

for arg in "$@"; do
  case "$arg" in
    --hn)
      GENERATE_HN=1
      ;;
  esac
done

if [ -z "$POST_PATH" ]; then
  echo "Usage: ./scripts/cope.sh <path-to-markdown-file>"
  echo "Example: ./scripts/cope.sh content/experiments/nemoclaw-memory-profiling.md --hn"
  exit 1
fi

if [ ! -f "$POST_PATH" ]; then
  echo "Error: File not found: $POST_PATH"
  exit 1
fi

# Extract frontmatter fields
TITLE=$(grep '^title:' "$POST_PATH" | head -1 | sed 's/title: *"*//;s/"*$//')
DESCRIPTION=$(grep '^description:' "$POST_PATH" | head -1 | sed 's/description: *"*//;s/"*$//')
TAGS=$(grep '^tags:' "$POST_PATH" | head -1 | sed 's/tags: *\[//;s/\]//')
DATE=$(date +%Y-%m-%d)

# Create output dirs
mkdir -p cope-drafts/linkedin cope-drafts/x cope-drafts/hn

SLUG=$(basename "$POST_PATH" .md)
SECTION=$(dirname "$POST_PATH" | sed 's|content/||')
POST_URL="https://zhanyl-tech.github.io/${SECTION}/${SLUG}/"

# ── Generate LinkedIn Draft ──
cat > "cope-drafts/linkedin/${SLUG}.md" << EOF
# LinkedIn Draft — ${DATE}
## For: ${TITLE}

---

### POST TEXT
### (Paste into LinkedIn body — NO external links here — upload diagram as native image)

${DESCRIPTION}

Here's what I found:

→ [Key insight 1 — rewrite as punchy 1-line bullet from the post]
→ [Key insight 2]
→ [Key insight 3]

[Deep dive: "Full technical breakdown with architecture diagrams and benchmarks on my blog."]
[Experiment: "Full results and raw data on my blog."]

#MLInfrastructure #HPC #GPU #QuantitativeFinance #CUDA #MachineLearning

---

### FIRST COMMENT
### (Post this immediately after publishing — this is where the link goes)

Full writeup with code and benchmarks: ${POST_URL}

---

### CHECKLIST
- [ ] Write specific insights (replace the bracket placeholders above)
- [ ] Upload diagram/screenshot as native image (NOT as a link)
- [ ] Paste post text
- [ ] Post Tuesday–Thursday 8–10 AM EST
- [ ] Immediately add first comment with blog link

EOF

# ── Generate X/Twitter Thread Draft ──
cat > "cope-drafts/x/${SLUG}.md" << EOF
# X Thread Draft — ${DATE}
## For: ${TITLE}

---

### THREAD — Post as individual tweets (attach diagram PNG to Tweet 1)

**Tweet 1 (Hook):**
[Surprising finding or contrarian claim from the post — the "wait, really?" moment]

[Attach: architecture diagram or terminal screenshot]

🧵👇

**Tweet 2:**
[Key technical insight — the mechanism that most people don't understand]

**Tweet 3:**
[Benchmark numbers or concrete data point — specifics build credibility]

**Tweet 4:**
[What most people get wrong about this — contrarian or corrective take]

**Tweet 5 (CTA):**
Full technical breakdown with code and benchmarks:

https://zhanyl-tech.github.io/$(dirname "$POST_PATH" | sed 's|content/||')/${SLUG}/

If this was useful, follow for more on GPU inference, ML infrastructure, and building at the intersection of HPC and quantitative finance.

---

### CHECKLIST
- [ ] Fill in the bracket placeholders with specific insights
- [ ] Attach diagram PNG to Tweet 1
- [ ] Post Wednesday 8–10 AM EST for peak engagement
- [ ] Each tweet must be under 280 chars

EOF

if [ "$GENERATE_HN" -eq 1 ]; then
cat > "cope-drafts/hn/${SLUG}.md" << EOF
# Hacker News Draft — ${DATE}
## For: ${TITLE}

### Suggested Title
${TITLE}

### URL
${POST_URL}

### Optional submission text
[1-3 sentences: why this is technically useful, what readers will learn, and why you wrote it.]

### CHECKLIST
- [ ] Only submit if this is a real deep dive worth HN attention
- [ ] Keep title factual, not hypey
- [ ] If discussion needs context, use a self-post

EOF
fi

echo ""
echo "✅ COPE drafts generated:"
echo "   LinkedIn: cope-drafts/linkedin/${SLUG}.md"
echo "   X Thread: cope-drafts/x/${SLUG}.md"
if [ "$GENERATE_HN" -eq 1 ]; then
  echo "   HN Draft:  cope-drafts/hn/${SLUG}.md"
fi
echo ""
echo "📝 Next steps:"
echo "   1. Edit both drafts — fill in the specific insights from your post"
echo "   2. Create visuals: architecture diagram or terminal screenshot"
echo "   3. Post LinkedIn: Tuesday–Thursday 8–10 AM EST"
echo "   4. Post X thread: Wednesday 8–10 AM EST"
if [ "$GENERATE_HN" -eq 1 ]; then
  echo "   5. Submit to HN if it's strong enough: news.ycombinator.com/submit"
else
  echo "   5. Re-run with --hn if this piece is HN-worthy"
fi
echo ""
