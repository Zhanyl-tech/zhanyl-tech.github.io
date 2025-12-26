# Zhanyl Abdybaeva - Personal Portfolio

**ML Infrastructure + Quantitative Finance Engineer**

Building AI-powered trading systems at the intersection of HPC, ML, and Quantitative Finance.

🌐 **Live Site:** [https://zhanyl-tech.github.io](https://zhanyl-tech.github.io)

---

## About This Site

Professional portfolio showcasing:
- **Projects:** DeFAI (Autonomous Trading Agent), CQF Quantitative Finance Research, HPC ML Inference Engine
- **Blog:** Technical articles on ML systems, quantitative finance, and trading infrastructure
- **Resume:** Tailored resumes for ML Infrastructure, Quant Research, and Trading Systems roles

---

## Technical Stack

- **Framework:** Jekyll 4.x with Minimal Mistakes theme
- **Hosting:** GitHub Pages
- **Content:** Markdown-based with YAML front matter
- **Styling:** Dark theme, mobile-responsive

---

## Local Development

### Prerequisites

- Ruby 2.7+ ([Install Ruby](https://www.ruby-lang.org/en/documentation/installation/))
- Bundler gem

### Setup

```bash
# Install dependencies
gem install bundler jekyll
bundle install

# Run local server
bundle exec jekyll serve

# View site at http://localhost:4000
```

### Building

```bash
# Build static site
bundle exec jekyll build

# Output in _site/ directory
```

---

## Site Structure

```
zhanyl-tech.github.io/
├── _config.yml              # Site configuration
├── index.md                 # Landing page
├── _pages/
│   ├── projects.md          # Projects showcase
│   ├── blog.md              # Blog index
│   └── resume.md            # Resume downloads
├── _posts/                  # Blog posts (date-named)
│   └── YYYY-MM-DD-title.md
├── assets/
│   ├── images/              # Images, screenshots
│   └── files/               # Resume PDFs
├── Gemfile                  # Ruby dependencies
└── README.md                # This file
```

---

## Adding Content

### New Blog Post

Create file: `_posts/YYYY-MM-DD-title.md`

```markdown
---
layout: single
title: "Your Post Title"
date: YYYY-MM-DD
categories: [ml, trading, finance]
tags: [python, pytorch, quantitative-finance]
---

Your content here...
```

### Update Projects

Edit: `_pages/projects.md`

### Update Resume PDFs

1. Place PDF files in `assets/files/`
2. Named: `Resume-ML-Infrastructure.pdf`, `Resume-Quant-Research.pdf`, `Resume-Trading-Systems.pdf`

### Add Images

1. Place images in `assets/images/`
2. Reference in markdown: `![Alt text](/assets/images/filename.jpg)`

---

## Deployment

### GitHub Pages

1. Push to `main` branch
2. GitHub Pages builds automatically
3. Site live at `https://zhanyl-tech.github.io` in 2-3 minutes

### Custom Domain (Optional)

1. Add `CNAME` file with your domain
2. Configure DNS A records to GitHub Pages IPs
3. Update `url` in `_config.yml`

---

## Configuration

Edit `_config.yml` to update:
- Site title and description
- Author bio and social links
- Theme settings
- Navigation menu
- SEO metadata

---

## Customization

### Theme

Change theme skin in `_config.yml`:
```yaml
minimal_mistakes_skin: "dark"  # Options: default, air, aqua, contrast, dark, dirt, neon, mint, plum, sunrise
```

### Navigation

Add/modify `_data/navigation.yml` for custom menu

### Analytics (Optional)

Add Google Analytics by updating `_config.yml`:
```yaml
analytics:
  provider: "google-gtag"
  google:
    tracking_id: "YOUR-TRACKING-ID"
```

---

## Maintenance

### Update Dependencies

```bash
bundle update
```

### Check Site Health

```bash
# Validate HTML
bundle exec jekyll build
# Check _site/ output

# Test links (optional)
gem install html-proofer
htmlproofer ./_site
```

---

## Resources

- [Jekyll Documentation](https://jekyllrb.com/docs/)
- [Minimal Mistakes Theme](https://mmistakes.github.io/minimal-mistakes/)
- [GitHub Pages Docs](https://docs.github.com/en/pages)
- [Markdown Guide](https://www.markdownguide.org/)

---

## Contact

**Zhanyl Abdybaeva**
- Email: your-email@example.com
- LinkedIn: [linkedin.com/in/yourprofile](https://linkedin.com/in/yourprofile)
- GitHub: [github.com/zhanyl-tech](https://github.com/zhanyl-tech)

---

## License

Content © 2025 Zhanyl Abdybaeva. All rights reserved.

Site built with [Jekyll](https://jekyllrb.com/) and [Minimal Mistakes](https://github.com/mmistakes/minimal-mistakes) theme.

