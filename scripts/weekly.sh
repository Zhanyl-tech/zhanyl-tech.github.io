#!/usr/bin/env bash
#
# weekly.sh — the weekly drop, end to end.
#
# GitHub is the system of record: the post is committed here, GitHub Pages
# publishes it, and the social drafts fan out from the committed version. One
# command, one review pass, done.
#
#   ./scripts/weekly.sh                            # newest draft
#   ./scripts/weekly.sh content/blog/my-post.md    # a specific post
#   ./scripts/weekly.sh --hn                       # also draft an HN submission
#   ./scripts/weekly.sh --dry-run                  # build and draft, don't push
#
set -euo pipefail

cd "$(dirname "$0")/.."

BOLD=$'\033[1m'; DIM=$'\033[2m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RED=$'\033[31m'; RESET=$'\033[0m'
step() { printf "\n${BOLD}%s${RESET}\n" "$1"; }
ok()   { printf "  ${GREEN}✓${RESET} %s\n" "$1"; }
warn() { printf "  ${YELLOW}!${RESET} %s\n" "$1"; }
die()  { printf "  ${RED}✗${RESET} %s\n" "$1" >&2; exit 1; }

POST=""
HN_FLAG=""
DRY_RUN=0

while [ $# -gt 0 ]; do
  case "$1" in
    --hn)      HN_FLAG="--hn" ;;
    --dry-run) DRY_RUN=1 ;;
    -h|--help) sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*)        die "unknown flag: $1" ;;
    *)         POST="$1" ;;
  esac
  shift
done

PY="./.venv/bin/python"
[ -x "$PY" ] || PY="python3"

# ── 1. Preflight ──────────────────────────────────────────────────────────────
step "1/6  Preflight"

command -v hugo >/dev/null || die "hugo not found (brew install hugo)"
command -v git  >/dev/null || die "git not found"
ok "hugo $(hugo version | grep -o 'v[0-9.]*' | head -1)"

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
ok "on branch ${BRANCH}"

if [ -z "${ANTHROPIC_API_KEY:-}" ] && [ ! -f .env ]; then
  warn "ANTHROPIC_API_KEY not set — drafts will use extraction, not Claude"
fi

# ── 2. Pick the post ──────────────────────────────────────────────────────────
step "2/6  Selecting post"

if [ -z "$POST" ]; then
  # Newest draft:true post across every writing section.
  POST="$(grep -rl '^draft: true' content/blog content/experiments content/notes 2>/dev/null \
          | xargs -r ls -t 2>/dev/null | head -1 || true)"
  [ -n "$POST" ] || die "no draft found. Pass a path, or set 'draft: true' on the post you want to ship."
  ok "newest draft: ${POST}"
else
  [ -f "$POST" ] || die "no such file: ${POST}"
  ok "${POST}"
fi

TITLE="$(grep -m1 '^title:' "$POST" | sed 's/title: *//; s/^"//; s/"$//')"
SLUG="$(basename "$POST" .md)"
printf "  ${DIM}%s${RESET}\n" "$TITLE"

# ── 3. Social preview card ────────────────────────────────────────────────────
step "3/6  Social preview card"
$PY scripts/ogimage.py --post "$POST"

# ── 4. Publish locally + verify the build ─────────────────────────────────────
step "4/6  Build"

if grep -q '^draft: true' "$POST"; then
  # BSD sed (macOS) needs the empty -i argument.
  sed -i '' 's/^draft: true/draft: false/' "$POST"
  ok "flipped draft: false"
else
  ok "already publishable"
fi

hugo --quiet --gc || die "hugo build failed — fix the error above, nothing was pushed"
ok "site builds"

BUILT="public/$(dirname "$POST" | sed 's|content/||')/${SLUG}/index.html"
[ -f "$BUILT" ] || die "post did not render at ${BUILT} — check the frontmatter date (buildFuture is off)"
ok "post renders"

grep -q 'og:image' "$BUILT" || warn "no og:image on this post — links will render bare"

# ── 5. Commit and push ────────────────────────────────────────────────────────
step "5/6  Publish to GitHub"

if [ "$DRY_RUN" -eq 1 ]; then
  warn "dry run — skipping commit and push"
else
  git add -A content static assets layouts hugo.yaml scripts 2>/dev/null || true

  if git diff --cached --quiet; then
    ok "nothing new to commit"
  else
    git commit -q -m "Publish: ${TITLE}"
    ok "committed"

    if git remote get-url origin >/dev/null 2>&1; then
      git push -q origin "$BRANCH"
      ok "pushed — GitHub Actions is building, live in ~2 min"
    else
      warn "no origin remote — commit is local only"
    fi
  fi
fi

# ── 6. Social drafts ──────────────────────────────────────────────────────────
step "6/6  Social drafts"
$PY scripts/social.py "$POST" $HN_FLAG

SECTION="$(dirname "$POST" | sed 's|content/||')"
URL="https://zhanyl-tech.github.io/${SECTION}/${SLUG}/"

cat <<EOF

${BOLD}Done.${RESET}  ${URL}

Review, then post:
  ${DIM}\$EDITOR cope-drafts/linkedin/${SLUG}.md${RESET}
  ${DIM}${PY} scripts/social.py ${POST} --copy linkedin --open${RESET}
  ${DIM}${PY} scripts/social.py ${POST} --copy x --open${RESET}

EOF
