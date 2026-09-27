#!/usr/bin/env bash
#
# preview.sh — review a draft locally, with its generated assets rendered.
#
#   ./scripts/preview.sh content/experiments/<slug>.md                # http://localhost:1313/
#   ./scripts/preview.sh content/experiments/<slug>.md --port 1414    # extra args go to hugo server
#
# vizpub keeps a post's generated images in cope-drafts/vizpub/<slug>/, which
# is gitignored and outside static/, so a plain `hugo server -D` shows the
# post's diagram as a broken image: the one generated file the post uses was
# never seen rendered before weekly.sh published it. This runs the same
# server with that directory mounted over static/ for this session only,
# through a throwaway config file passed after hugo.yaml. Nothing is copied
# into static/ and nothing in the repository changes.
#
# Hugo drops a component's default mount once a project mounts anything into
# it, so the config mounts static/ explicitly as well
# (https://gohugo.io/configuration/module/, "Defining a mount for a component
# within a project configuration removes the default mount for that
# component"). Files passed to --config combine left to right, the last one
# winning a conflicting key (https://gohugo.io/configuration/introduction/).
#
set -euo pipefail

cd "$(dirname "$0")/.."

die() { printf "  ✗ %s\n" "$1" >&2; exit 1; }

[ $# -ge 1 ] || die "pass the draft to preview, e.g. ./scripts/preview.sh content/experiments/my-post.md"
POST="$1"
shift
[ -f "$POST" ] || die "no such file: ${POST}"
command -v hugo >/dev/null || die "hugo not found (the site is built with Hugo 0.159.0 extended)"

SLUG="$(basename "$POST" .md)"
REVIEW_DIR="cope-drafts/vizpub/${SLUG}"

if [ ! -d "$REVIEW_DIR" ]; then
  printf "  previewing %s (no generated assets in %s)\n" "$POST" "$REVIEW_DIR"
  exec hugo server -D "$@"
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
CONFIG="${TMP_DIR}/preview.yaml"
cat >"$CONFIG" <<YAML
module:
  mounts:
    - source: static
      target: static
    - source: ${REVIEW_DIR}
      target: static
YAML

printf "  previewing %s with %s mounted over static/\n" "$POST" "$REVIEW_DIR"
hugo server -D --config "hugo.yaml,${CONFIG}" "$@"
