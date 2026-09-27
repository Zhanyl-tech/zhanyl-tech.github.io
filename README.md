# zhanyl-tech.github.io

Personal site of [Zhanyl Abdybaeva](https://zhanyl-tech.github.io): GPU
scheduling across Slurm and Kubernetes, GPU fleet-health tooling, and the
benchmarks that check them. Every project page states whether the work is
built, partial or planned; errors are listed on
[/corrections/](https://zhanyl-tech.github.io/corrections/).

Built with [Hugo](https://gohugo.io) **0.159.0 extended** and the
[PaperMod](https://github.com/adityatelange/hugo-PaperMod) theme (a git
submodule), deployed by GitHub Actions to GitHub Pages.

## Local development

```bash
git clone --recurse-submodules https://github.com/Zhanyl-tech/zhanyl-tech.github.io
cd zhanyl-tech.github.io
hugo server -D                      # drafts included, http://localhost:1313/
scripts/preview.sh content/experiments/<slug>.md  # same, with a vizpub draft's generated images
hugo --minify -d public             # what CI builds (CI adds --panicOnWarning)
python3 scripts/linkcheck.py public # every internal link, #fragment, og:image and feed link must resolve
```

Checks that CI runs on every pull request and push (`.github/workflows/deploy.yml`):

```bash
python3 scripts/check_content.py              # review marker; stage/status; branch refs; withdrawn wording
python3 scripts/static_diagrams.py --check    # still twins of animated diagrams are current
python3 -m unittest discover -s scripts/tests # tests for the publishing scripts
hugo --minify --panicOnWarning
python3 scripts/linkcheck.py public
```

All of these are standard library only, and run on Python 3.9 (macOS's
`python3`) as well as 3.12 (CI's).

## Layout

```
content/          pages; projects/ carry `status` (text) and `stage` (built|partial|planned)
layouts/          overrides of PaperMod: homepage, head (title), Open Graph, JSON-LD,
                  RSS, image render hook (reduced-motion diagrams), contact form
assets/css/       the site stylesheet (extends PaperMod)
static/images/    system map, diagrams (+ .static.svg still twins), social cards
scripts/          publishing tools and checks (see PUBLISH.md)
hugo.yaml         site config, including the homepage proof tiles (params.proof)
```

Local overrides of theme files say which theme commit they were copied from.
When the PaperMod submodule moves, re-diff them.

## Publishing

See [PUBLISH.md](PUBLISH.md). In short: drafts are reviewed locally, published
through a `publish/<slug>` branch and a pull request, and never pushed to `main`
by a script.

## Scripts

| script | does |
| --- | --- |
| `weekly.sh` | publish one reviewed post through a pull request |
| `preview.sh` | `hugo server -D` with a draft's generated assets mounted, for review |
| `post_assets.py` | which generated files a post references, and so publishes |
| `vizpub.py` | generate a draft post and assets with Claude (`claude-opus-5`); drafts only |
| `social.py` | LinkedIn / X / HN drafts from a post (Claude or extraction) |
| `ogimage.py` | 1200×630 social cards (rsvg-convert, or resvg-py with `OG_FONT_DIR`) |
| `static_diagrams.py` | animation-free twins of the animated diagrams |
| `check_content.py` | content rules the build cannot enforce, including wording the site withdrew |
| `linkcheck.py` | internal link, fragment, social-card and feed check of a build |
| `last_published.py` | date of the newest published post (used by `weekly-drop`) |
| `logo.py` | the mark and favicons |
| `cope.sh`, `favicons.py` | deprecated |

## License

<!-- OWNER: no license is declared for the site's content. Choose one (for
example CC BY 4.0 for the writing and MIT for the scripts) or state "all
rights reserved". -->
No license has been declared yet. The linked project repositories carry their
own (MIT).
