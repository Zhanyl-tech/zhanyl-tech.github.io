# Publishing workflow

## The one rule

**Nothing reaches the site without a person reading it first, and nothing is
pushed to `main` by a script.** `main` is what GitHub Pages deploys, so a push
to `main` is a publish. Every path below ends in a pull request.

- `vizpub.py` generates drafts. Its posts are always `draft: true` and carry a
  review marker (`VIZPUB-REVIEW-TODO`); its images, slides and PDFs go to
  `cope-drafts/vizpub/<slug>/`, which is gitignored, not to `static/`, because
  Hugo serves everything under `static/` whether or not a post is a draft.
- `scripts/check_content.py` (run in CI and by `weekly.sh`) fails while a
  published post still carries the marker.
- `weekly.sh` needs a terminal, shows you the post and opens each generated
  file the post references, asks you to type its slug, and pushes a
  `publish/<slug>` branch. Only those referenced files are copied into
  `static/`; the rest of `cope-drafts/vizpub/<slug>/` stays unpublished.
  Merging the pull request deploys.
- The Saturday `weekly-drop` workflow only opens a checklist issue. Its token
  cannot push, and it runs no generator.

## Step 1 — Write, or generate a draft

By hand:

```bash
hugo new experiments/$(date +%F)-slug.md   # keep draft: true while writing
```

Or generate one from a topic and papers (needs `ANTHROPIC_API_KEY` in the
environment or `.env`; uses `claude-opus-5`):

```bash
.venv/bin/python scripts/vizpub.py \
  --topic "How vLLM schedules KV cache memory" \
  --section blog \
  --paper https://arxiv.org/abs/2309.06180
```

What it writes:

- `content/blog/<slug>.md` — the draft (`draft: true`, review marker at the end)
- `cope-drafts/vizpub/<slug>/images/vizpub/<slug>.svg|.png|.mmd` — overview
  graphic and diagram
- `cope-drafts/vizpub/<slug>/images/slides/<slug>-0N.svg`,
  `cope-drafts/vizpub/<slug>/slides/<slug>.html|.pdf` — slides
- `cope-drafts/linkedin/<slug>.md`, `cope-drafts/x/<slug>.md`,
  `cope-drafts/hn/<slug>.md` — social drafts

Model output is untrusted input: the slug is sanitised, generated SVG has
scripts, event handlers and external links stripped, and every claim still
needs checking against the sources before the marker comes out.

## Step 2 — Review locally

```bash
scripts/preview.sh content/blog/<slug>.md   # drafts included; http://localhost:1313/
```

This is `hugo server -D` with `cope-drafts/vizpub/<slug>/` mounted over
`static/` for the session, so the post's generated diagram renders where it
will be published. With plain `hugo server -D` it is a broken image, because
nothing generated is in `static/` until step 3.

Read the post rendered. Check every number against its source. Replace the
`VIZPUB-REVIEW-TODO` comment with a true disclosure, for example
*"Drafted with an LLM; every claim checked against the sources above on
YYYY-MM-DD."*

## Step 3 — Publish through a pull request

```bash
./scripts/weekly.sh content/blog/<slug>.md          # --hn for a Hacker News draft
./scripts/weekly.sh content/blog/<slug>.md --dry-run
```

It shows the post, lists and opens the generated files the post references
(`scripts/post_assets.py`: files it names by site path, and what a referenced
page such as the slides page links), and asks for the slug, which confirms the
post and those files together. It then renders the social card, copies only
those files from `cope-drafts/vizpub/<slug>/` into `static/`, flips
`draft: false`, runs the content checks, builds the site and link-checks it,
then commits only the post, its card and its assets to `publish/<slug>` and
pushes that branch. `WEEKLY_NO_OPEN=1` lists the files without opening them.
vizpub's overview graphic, slides and PDF are published only if you link them
from the post. Open the pull request; CI builds and link-checks it again;
merging it deploys (about two minutes).

## Step 4 — Post on LinkedIn, X and Hacker News (manual)

`weekly.sh` finishes by running `scripts/social.py`, which drafts from the
post's own text (with Claude when a key is set, by extraction otherwise).

- **LinkedIn:** paste `cope-drafts/linkedin/<slug>.md`; put the link in the
  first comment, not the body. Tuesday–Thursday, 8–10 AM ET.
- **X:** `cope-drafts/x/<slug>.md`; link on the last tweet.
- **Hacker News:** deep dives only; `cope-drafts/hn/<slug>.md`.

`scripts/social.py <post> --copy linkedin --open` copies a draft and opens the
site.

## Deprecated

- `scripts/cope.sh` — bracket-placeholder templates; `social.py` replaced it.
- `scripts/favicons.py` — the old monogram; `scripts/logo.py` owns the
  favicons. It refuses to run without `--force`.
