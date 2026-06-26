# Jobpin Agent (product source)

The actual Jobpin Agent product — a local-first, AI-agent HR platform.
This directory is **not** part of the Netlify-deployed docs site.

- Product requirements: `../site/plan/01-PRD-EN.md`
- Delivery roadmap: `../site/plan/02-Production-Plan-EN.md`
- Hermes porting source (read-only): `../reference/hermes/`
- License hygiene for ported code: `THIRD_PARTY_NOTICES.md`

## Dev quickstart

```bash
cd agent
python -m pytest        # runs the smoke test
```

Internal structure (Agent Core, Memory Subsystem, sub-agents, orchestration)
is built in Phase 0 of the Production Plan and intentionally not scaffolded yet.
