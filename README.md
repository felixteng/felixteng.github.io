# Fei Teng — Academic Homepage

Bilingual (English / 中文) academic website built with [Hugo](https://gohugo.io/) and a lightweight custom theme. Deployed to GitHub Pages via GitHub Actions.

## Local development

```bash
hugo server -D        # http://localhost:1313  (live reload)
```

## How to update content

| Task | What to edit |
|------|--------------|
| Add / edit a publication | `data/publications.yaml` (set `featured: true` to show on home) |
| Add / edit a student or alumnus | `data/students.yaml` |
| Post a news item | add `content/news/<slug>.en.md` and `.zh.md` |
| Edit bio (home) | `content/_index.en.md` / `.zh.md` |
| Edit a section (research, teaching, service, cv, contact) | `content/<section>/_index.en.md` / `.zh.md` |
| Add headshot | put image in `static/img/`, set `params.photo` in `hugo.toml` |
| Add CV PDF | put file in `static/cv/`, uncomment the link in `content/cv/_index.*.md` |

## Bilingual notes

- Each content page has an `.en.md` and a `.zh.md` version.
- UI strings live in `i18n/en.yaml` and `i18n/zh.yaml`.
- Data files use bilingual fields (`name_en` / `name_zh`, `research_en` / `research_zh`).
- First-time visitors are auto-routed to `/en/` or `/zh/` by browser language; the header switch lets them override (choice stored in `localStorage`).

## Deploy

Push to `main` → GitHub Actions builds and publishes automatically. In the repo, set **Settings → Pages → Source = GitHub Actions** once.
