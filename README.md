# Jobpin Agent

Monorepo for **Jobpin Agent** — a local-first, AI-agent HR platform — plus the
public docs site that presents its PRD and Production Plan.

## Layout

| Path | What it is | Deployed? |
|---|---|---|
| `site/` | Zero-build static docs viewer (PRD + Production Plan) | ✅ Netlify publishes **only** this |
| `site/plan/` | Canonical PRD + Production Plan markdown (served by the viewer) | ✅ (inside `site/`) |
| `agent/` | The actual product source (Python) | ❌ never published |
| `reference/hermes/` | Hermes Agent source (MIT), pinned submodule, **porting reference only** | ❌ never published |
| `docs/superpowers/` | Internal specs & implementation plans | ❌ never published |

## Docs site

Static, no build. Netlify (`netlify.toml`) serves `site/` as the web root. Run
locally over HTTP — the viewer fetches markdown, which needs HTTP not `file://`:

```bash
python -m http.server 8123 --directory site
# open http://localhost:8123/
```

Edit the markdown in `site/plan/` and redeploy. No build, no duplicate copies.

| Document | English | 中文 |
|---|---|---|
| PRD | `site/plan/01-PRD-EN.md` | `site/plan/01-PRD.md` |
| Production Plan | `site/plan/02-Production-Plan-EN.md` | `site/plan/02-Production-Plan.md` |

The feedback form only truly submits on the deployed Netlify site (it posts to
Netlify Forms); locally you can see it render and validate. The site is marked
`noindex` — treat the URL as unlisted.

## Product (agent/)

```bash
cd agent
python -m pytest
```

See `agent/README.md`. Hermes is ported **into** `agent/`, never depended on at
runtime; ported files keep their MIT notice in `agent/THIRD_PARTY_NOTICES.md`.

## Working with the Hermes submodule

```bash
git submodule update --init --recursive   # populate reference/hermes/
```
