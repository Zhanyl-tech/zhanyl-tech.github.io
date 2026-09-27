#!/usr/bin/env bash
#
# weekly.sh — publish one reviewed post, through a pull request.
#
#   ./scripts/weekly.sh content/blog/my-post.md            # the post to publish
#   ./scripts/weekly.sh content/blog/my-post.md --hn       # also draft an HN submission
#   ./scripts/weekly.sh content/blog/my-post.md --dry-run  # everything except commit and push
#   WEEKLY_NO_OPEN=1 ./scripts/weekly.sh ...                # list the generated files, open them yourself
#
# What changed in September 2026, and why:
#   - The post is an explicit argument. Picking "the newest draft" by mtime
#     meant a freshly generated, unread vizpub draft could be the one published.
#   - Nothing is pushed to main. The script commits to a publish/<slug> branch
#     and pushes that; the site deploys only when a pull request is merged.
#     main is what GitHub Pages deploys, so a direct push was a direct publish.
#   - Before anything is committed it prints the post and asks you to type the
#     slug back. It refuses a post that still carries vizpub's review marker.
#   - It stages only this post, its social card and the assets it owns, never
#     `git add -A static`: anything under static/ is served whether or not a
#     post is a draft.
#   - "The assets it owns" means the generated files the post references
#     (scripts/post_assets.py), not everything vizpub left in
#     cope-drafts/vizpub/<slug>/. They are listed and opened before the slug
#     confirmation, so what is confirmed is everything that goes live. Copying
#     the whole directory used to publish slides, a PDF and an overview
#     graphic that the review step never showed anyone.
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
REVIEW_MARKER="VIZPUB-REVIEW-TODO"   # keep in step with scripts/vizpub.py

while [ $# -gt 0 ]; do
  case "$1" in
    --hn)      HN_FLAG="--hn" ;;
    --dry-run) DRY_RUN=1 ;;
    -h|--help) sed -n '2,27p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*)        die "unknown flag: $1" ;;
    *)         POST="$1" ;;
  esac
  shift
done

PY="./.venv/bin/python"
[ -x "$PY" ] || PY="python3"

# Scratch space for the asset list and the check build, removed on any exit.
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

# ── 1. Preflight ──────────────────────────────────────────────────────────────
step "1/7  Preflight"

[ -n "$POST" ] || die "pass the post to publish, e.g. ./scripts/weekly.sh content/blog/my-post.md"
[ -f "$POST" ] || die "no such file: ${POST}"
case "$POST" in
  content/blog/*.md|content/experiments/*.md|content/notes/*.md) ;;
  *) die "not a post under content/{blog,experiments,notes}/: ${POST}" ;;
esac

command -v hugo >/dev/null || die "hugo not found (the site is built with Hugo 0.159.0 extended)"
command -v git  >/dev/null || die "git not found"
ok "hugo $(hugo version | grep -o 'v[0-9.]*' | head -1)"

if [ -n "$(git status --porcelain -- "$POST")" ] && [ "$DRY_RUN" -eq 0 ]; then
  ok "post has local changes; they will be part of this publish"
fi

if [ -z "${ANTHROPIC_API_KEY:-}" ] && [ ! -f .env ]; then
  warn "ANTHROPIC_API_KEY not set — social drafts will use extraction, not Claude"
fi

TITLE="$(grep -m1 '^title:' "$POST" | sed 's/title: *//; s/^"//; s/"$//')"
SLUG="$(basename "$POST" .md)"
SECTION="$(dirname "$POST" | sed 's|content/||')"

# ── 2. Review gate ────────────────────────────────────────────────────────────
step "2/7  Review"

if grep -q "$REVIEW_MARKER" "$POST"; then
  die "the post still contains ${REVIEW_MARKER}; replace it with a real disclosure first"
fi

# A person has to be here: no terminal, no publish. This is what keeps a
# scheduled job, or anything else without a human, from using this script.
[ -t 0 ] || die "no terminal to confirm on; weekly.sh only publishes interactively"

printf "  ${DIM}%s${RESET}\n\n" "$TITLE"
${PAGER:-less} "$POST" || true

# The generated files this post publishes: only those under
# cope-drafts/vizpub/<slug>/ that the post references, directly or through a
# referenced page. They are listed and opened now, so the confirmation below
# covers them as well as the text.
REVIEW_DIR="cope-drafts/vizpub/${SLUG}"
ASSET_RELS=()
if [ -d "$REVIEW_DIR" ]; then
  ASSET_LIST="${WORK_DIR}/assets"
  $PY scripts/post_assets.py "$POST" --review-dir "$REVIEW_DIR" -0 >"$ASSET_LIST" \
    || die "could not work out which generated assets the post uses; nothing changed"
  while IFS= read -r -d '' rel; do
    ASSET_RELS+=("$rel")
  done <"$ASSET_LIST"

  LEFT="$($PY scripts/post_assets.py "$POST" --review-dir "$REVIEW_DIR" --unreferenced)"
  if [ -n "$LEFT" ]; then
    warn "not published, because the post does not reference them:"
    printf "%s\n" "$LEFT" | sed 's/^/      /'
  fi
fi

if [ "${#ASSET_RELS[@]}" -gt 0 ]; then
  printf "\n  This post publishes %d generated file(s). Check each one:\n" "${#ASSET_RELS[@]}"
  for rel in "${ASSET_RELS[@]}"; do
    printf "    %s/%s  ->  static/%s\n" "$REVIEW_DIR" "$rel" "$rel"
  done
  if [ -n "${WEEKLY_NO_OPEN:-}" ]; then
    : # the reviewer asked to open them by hand
  elif [ "$(uname)" = "Darwin" ] && command -v open >/dev/null; then
    for rel in "${ASSET_RELS[@]}"; do open "${REVIEW_DIR}/${rel}" || true; done
  elif command -v xdg-open >/dev/null; then
    for rel in "${ASSET_RELS[@]}"; do xdg-open "${REVIEW_DIR}/${rel}" >/dev/null 2>&1 || true; done
  else
    warn "no opener found; open the files above yourself before confirming"
  fi
  printf "\n  Type the slug (%s) to confirm you have read this post, checked these %d file(s), and want them published: " \
    "$SLUG" "${#ASSET_RELS[@]}"
else
  printf "  Type the slug (%s) to confirm you have read this post and want it published: " "$SLUG"
fi
read -r CONFIRM
[ "$CONFIRM" = "$SLUG" ] || die "not confirmed; nothing changed"
ok "confirmed"

# ── 3. Social preview card ────────────────────────────────────────────────────
step "3/7  Social preview card"
$PY scripts/ogimage.py --post "$POST"
CARD="static/images/og/${SLUG}.png"

# ── 4. Reviewed assets ────────────────────────────────────────────────────────
# vizpub keeps generated images, slides and PDFs in cope-drafts/vizpub/<slug>/
# in the same layout they will have under static/. Only the files listed and
# confirmed in step 2 go live, and only now.
step "4/7  Assets"
ASSETS=()
if [ "${#ASSET_RELS[@]}" -gt 0 ]; then
  for rel in "${ASSET_RELS[@]}"; do
    mkdir -p "static/$(dirname "$rel")"
    cp "${REVIEW_DIR}/${rel}" "static/${rel}"
    ASSETS+=("static/${rel}")
  done
  ok "copied ${#ASSETS[@]} reviewed asset(s) from ${REVIEW_DIR}"
else
  ok "no generated assets for this post"
fi

# ── 5. Build and check ────────────────────────────────────────────────────────
step "5/7  Build"

if grep -q '^draft: true' "$POST"; then
  # BSD sed (macOS) needs the empty -i argument.
  sed -i '' 's/^draft: true/draft: false/' "$POST"
  ok "flipped draft: false"
else
  ok "already publishable"
fi

$PY scripts/check_content.py || die "content checks failed — nothing was committed"
BUILD_DIR="${WORK_DIR}/public"
hugo --quiet --gc -d "$BUILD_DIR" || die "hugo build failed — fix the error above, nothing was committed"
ok "site builds"

BUILT="${BUILD_DIR}/${SECTION}/${SLUG}/index.html"
[ -f "$BUILT" ] || die "post did not render at ${BUILT} — check the front-matter date (buildFuture is off)"
ok "post renders"
grep -q 'og:image' "$BUILT" || warn "no og:image on this post — links will render bare"
$PY scripts/linkcheck.py "$BUILD_DIR" || die "broken internal links — nothing was committed"

# ── 6. Commit to a branch, push, open a PR by hand ────────────────────────────
step "6/7  Publish branch"

if [ "$DRY_RUN" -eq 1 ]; then
  warn "dry run — nothing committed or pushed (the draft flag and copied assets are left in the working tree)"
else
  CURRENT="$(git rev-parse --abbrev-ref HEAD)"
  TARGET="publish/${SLUG}"
  if [ "$CURRENT" != "$TARGET" ]; then
    git switch -c "$TARGET" >/dev/null 2>&1 || git switch "$TARGET" >/dev/null
  fi
  git add -- "$POST"
  [ -f "$CARD" ] && git add -- "$CARD"
  [ "${#ASSETS[@]}" -gt 0 ] && git add -- "${ASSETS[@]}"

  echo
  git --no-pager diff --cached --stat
  echo
  if git diff --cached --quiet; then
    ok "nothing new to commit"
  else
    git commit -q -m "Publish: ${TITLE}"
    ok "committed on ${TARGET}"
    if git remote get-url origin >/dev/null 2>&1; then
      git push -q -u origin "$TARGET"
      ok "pushed ${TARGET}. Open a pull request into main; merging it deploys the site."
    else
      warn "no origin remote — commit is local only"
    fi
  fi
fi

# ── 7. Social drafts ──────────────────────────────────────────────────────────
step "7/7  Social drafts"
$PY scripts/social.py "$POST" $HN_FLAG

URL="https://zhanyl-tech.github.io/${SECTION}/${SLUG}/"

cat <<EOF

${BOLD}Done.${RESET}  ${URL} (live once the pull request is merged)

Review, then post:
  ${DIM}\$EDITOR cope-drafts/linkedin/${SLUG}.md${RESET}
  ${DIM}${PY} scripts/social.py ${POST} --copy linkedin --open${RESET}
  ${DIM}${PY} scripts/social.py ${POST} --copy x --open${RESET}

EOF
