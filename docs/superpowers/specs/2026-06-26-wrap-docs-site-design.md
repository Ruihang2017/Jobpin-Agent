# Design: Wrap the docs site and open a home for the Jobpin Agent product

| Item | Value |
|---|---|
| Date | 2026-06-26 |
| Status | Approved (brainstorming output) |
| Author | horace.hou |
| Related | `site/plan/01-PRD-EN.md` (PRD §2.3–2.7, §8–9), `site/plan/02-Production-Plan-EN.md` (Phase 0) |

## 1. Context & problem

The repository is currently a **zero-build static docs site** whose only purpose is to show
people the PRD and Production Plan. `index.html` + `assets/` render the markdown in `plan/`
at runtime via `fetch()`. Netlify deploys it with `publish = "."` and an empty build
command — i.e. **the entire repo root is served as-is**.

We now want to build the **actual product** (a Python, local-first, AI-agent HR platform — see
the PRD) **in this same repository**, without disturbing the live docs deployment. The product
strongly references the Hermes Agent (Nous Research, MIT) and will **port specific files** from
it; the Production Plan cites real Hermes paths and line numbers, so the Hermes source must be
available as porting reference.

## 2. Constraints

- **Netlify serves the repo root** (`publish = "."`). Anything added at the root becomes publicly
  reachable on the live site. Today this even exposes `docs/superpowers/` internal plans.
- **Auto-deploy**: pushes to `main` deploy automatically, so structural changes must be done on a
  branch with a deploy preview, then merged.
- **Zero-build must be preserved** — no bundler/build step is wanted for the docs site.
- **Public output must stay identical**: same rendered site, same public URLs.
- **Hermes is MIT**: free to port within a closed-source commercial product, with the sole
  obligation to retain the copyright + license notice in substantial copied portions
  (PRD §2.7). It is a **porting source, never a runtime dependency** ("own the backbone").

## 3. Decisions (locked with the user)

1. **Monorepo, flat layout**: `site/` (the only thing Netlify publishes) + `agent/` (the Python
   product) + `reference/hermes/` (porting source).
2. **Hermes as a pinned git submodule** at `reference/hermes/`, fixed to the latest commit on the
   upstream default branch at setup time, so every developer and coding agent ports against the exact
   same source the Plan cites. (The pin can be advanced later with an explicit commit.)
3. **`plan/` markdown moves into `site/plan/`** — it is both the canonical home of the PRD/Plan and
   the content the site serves; keeping it inside the publish dir preserves the zero-build runtime
   `fetch()`.
4. **`netlify.toml`**: `publish = "."` → `publish = "site"` (the only config change).

## 4. Target layout

```
Jobpin-Agent/
├─ netlify.toml              # publish = "site"   (changed from ".")
├─ README.md                 # rewritten as a monorepo overview
├─ .gitignore                # + Python ignores
├─ .gitmodules               # records the pinned Hermes submodule
│
├─ site/                     # ← the ONLY thing Netlify publishes (today's docs viewer)
│   ├─ index.html
│   ├─ assets/  (app.js, feedback.js, render.js, style.css, vendor/…)
│   └─ plan/                 # PRD + Production Plan markdown (served at runtime + canonical)
│       ├─ 01-PRD-EN.md / 01-PRD.md
│       └─ 02-Production-Plan-EN.md / 02-Production-Plan.md
│
├─ agent/                    # ← the Python product (NOT published) — minimal placeholder now
│   ├─ README.md
│   ├─ pyproject.toml
│   ├─ src/jobpin_agent/__init__.py
│   ├─ tests/test_smoke.py
│   └─ THIRD_PARTY_NOTICES.md   # MIT notice for code ported from Hermes
│
├─ reference/
│   └─ hermes/               # ← git submodule, pinned commit (read-only porting reference)
│
└─ docs/superpowers/…        # internal specs/plans (no longer public after the switch)
```

## 5. Migration steps (one atomic commit on the `chore/wrap-docs-site` branch)

1. `git mv index.html site/index.html`; `git mv assets site/assets`; `git mv plan site/plan`.
2. Edit `netlify.toml`: `publish = "."` → `publish = "site"`. Keep `command = ""` and the
   `noindex` headers block.
3. Add the `agent/` skeleton: `pyproject.toml`, `src/jobpin_agent/__init__.py`, `tests/test_smoke.py`,
   `README.md`, `THIRD_PARTY_NOTICES.md` (stub naming Hermes MIT + which files will be derived).
4. `git submodule add https://github.com/NousResearch/hermes-agent.git reference/hermes` (records the
   current upstream default-branch commit as the pin); creates `.gitmodules`.
5. Extend `.gitignore` with Python entries (`__pycache__/`, `*.pyc`, `.venv/`, `.pytest_cache/`,
   `*.egg-info/`); rewrite root `README.md` as a monorepo overview.

## 6. Invariants & guarantees

- **Only `site/` is published.** Product source, the Hermes submodule, and `docs/superpowers/`
  internal plans are all outside the publish dir → never public.
- **Public URLs unchanged.** `https://<site>/` → `site/index.html`; `https://<site>/plan/01-PRD-EN.md`
  → `site/plan/01-PRD-EN.md`. The relative `fetch()` paths in `assets/app.js` are unaffected because
  the site's structure relative to its web root is unchanged.
- **Byte-identical rendered output** — no build step introduced.
- **Hermes never becomes a runtime dependency** and is never published.
- **License hygiene from day one**: ported files will carry the MIT notice in
  `agent/THIRD_PARTY_NOTICES.md`.

## 7. Out of scope (YAGNI)

- The internal structure of `agent/` (Agent Core, Memory Subsystem, sub-agents, Layer B
  orchestration) — that is **Phase 0 of the Production Plan** and gets its own brainstorm/spec.
- Actually porting the Hermes files (`memory_tool.py`, `memory_provider.py`, `memory_manager.py`,
  `threat_patterns.py`).
- Any product feature, model wiring, or dependency selection.

## 8. Verification

1. Serve `site/` over HTTP locally (the runtime `fetch()` needs HTTP, not `file://`); confirm the
   page renders and both the PRD and Production Plan markdown load in EN and 中文.
2. Confirm `netlify.toml` → `publish = "site"`.
3. Before merging to `main`: open a Netlify **deploy preview** for the branch and confirm it matches
   production (same pages, same URLs).

## 9. Risks & mitigations

- **`git submodule add` needs network access to github.com.** If unavailable in the working
  environment, the restructure still completes; document the exact submodule command for the user to
  run, and leave `reference/hermes/` to be populated then.
- **Moving files on `main` would trigger an immediate deploy.** Mitigation: all work happens on
  `chore/wrap-docs-site`; merge only after the deploy preview is confirmed.
- **Wrong submodule path inside `site/`** would publish Hermes source. Mitigation: submodule lives at
  `reference/hermes/`, outside the publish dir; verified by inspecting the deploy preview's file list.
