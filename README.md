# Jobpin Agent — PRD Review Site

A zero-build static site that renders the Jobpin Agent PRD and Production Plan
(English + 中文) and collects reviewer feedback via Netlify Forms. The site reads
the markdown in `plan/` directly — there is no build step and no duplicate copies.

## Run locally

The page fetches markdown over HTTP, so it needs a static server (not `file://`):

```bash
python -m http.server 8080
# then open http://localhost:8080
```

Note: the feedback form only truly submits on the deployed Netlify site (it posts
to Netlify's form backend). Locally you can see it render and validate.

## Deploy to Netlify

- **Git:** push this repo, then Netlify → "Add new site → Import from Git" → pick the
  repo. Build command: none. Publish directory: `.` (already set in `netlify.toml`).
- **Drag & drop:** drag the project folder into the Netlify dashboard.

After the first deploy:
1. Netlify → site → **Forms** → confirm a form named `feedback` is listed.
2. Forms → notifications → add an email notification to receive reviewer comments.
3. Share the URL (it's marked `noindex`; treat it as unlisted).

## Update content

Edit the markdown in `plan/` and redeploy. No build, no copies.

| Document | English | 中文 |
|---|---|---|
| PRD | `plan/01-PRD-EN.md` | `plan/01-PRD.md` |
| Production Plan | `plan/02-Production-Plan-EN.md` | `plan/02-Production-Plan.md` |
