# Wrap Docs Site + Open Agent Product Home — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the repo into a flat monorepo (`site/` published by Netlify + `agent/` for the Python product) with Hermes as a pinned submodule, without changing the live docs site's output.

**Architecture:** Move the existing zero-build docs viewer into `site/` and re-point Netlify's `publish` dir at it, so only `site/` is public. Add a minimal `agent/` Python skeleton as the product's home, and add the Hermes source as a read-only pinned submodule under `reference/` for porting.

**Tech Stack:** Static HTML/JS (existing docs site), Python ≥ 3.11 (agent skeleton, `pyproject.toml` + `src/` layout, `pytest`), Netlify (zero-build static hosting), git submodules.

## Global Constraints

- Netlify `publish` must point at `site` only; `command` stays empty (zero-build preserved).
- Public output and public URLs must stay identical (`/` and `/plan/*.md` resolve as before).
- Hermes lives at `reference/hermes/` (outside the publish dir), is a porting **reference only**, never a runtime dependency, never published.
- All work happens on branch `chore/wrap-docs-site`; do **not** merge to `main` until a Netlify deploy preview is confirmed.
- Ported Hermes code (future work) must retain the MIT notice in `agent/THIRD_PARTY_NOTICES.md` (PRD §2.7).
- Hermes upstream: `https://github.com/NousResearch/hermes-agent.git`, pinned to the current default-branch commit at setup.

---

## File Structure

- `site/index.html`, `site/assets/**`, `site/plan/*.md` — the moved docs viewer (only published tree).
- `netlify.toml` — one-line change: `publish = "site"`.
- `agent/pyproject.toml`, `agent/src/jobpin_agent/__init__.py`, `agent/tests/test_smoke.py`, `agent/README.md`, `agent/THIRD_PARTY_NOTICES.md` — minimal Python product home.
- `reference/hermes/` — git submodule (pinned).
- `.gitmodules` — submodule record (git-generated).
- `.gitignore` — add Python ignores.
- `README.md` — rewritten monorepo overview.

---

### Task 1: Move the docs site into `site/` and re-point Netlify

**Files:**
- Move: `index.html` → `site/index.html`
- Move: `assets/` → `site/assets/`
- Move: `plan/` → `site/plan/`
- Modify: `netlify.toml` (publish dir)

**Interfaces:**
- Consumes: nothing.
- Produces: a `site/` tree whose web-root-relative layout matches today's repo root, so `assets/app.js`'s `fetch('plan/<doc>.md')` still resolves. Netlify serves `site/` as web root.

- [ ] **Step 1: Move the three site pieces with git (preserves history)**

```bash
git mv index.html site/index.html
git mv assets site/assets
git mv plan site/plan
```

- [ ] **Step 2: Re-point Netlify at `site/`**

Edit `netlify.toml`, change only the publish line:

```toml
# Zero-build static site. Netlify serves the site/ folder as-is.
[build]
  publish = "site"
  command = ""

# Keep the unlisted review site out of search indexes.
[[headers]]
  for = "/*"
  [headers.values]
    X-Robots-Tag = "noindex, nofollow"
```

- [ ] **Step 3: Verify the moved tree (structure check = the test for a move)**

Run: `git status --short && ls site && ls site/assets && ls site/plan`
Expected: `index.html`, `assets/`, `plan/` now under `site/`; root no longer has them; `netlify.toml` modified.

- [ ] **Step 4: Serve `site/` over HTTP and confirm it renders + fetches markdown**

Run (background server, then probe):
```bash
python -m http.server 8123 --directory site &
sleep 1
curl -s -o /dev/null -w "index:%{http_code}\n" http://localhost:8123/
curl -s -o /dev/null -w "prd-en:%{http_code}\n" http://localhost:8123/plan/01-PRD-EN.md
curl -s -o /dev/null -w "plan-zh:%{http_code}\n" http://localhost:8123/plan/02-Production-Plan.md
kill %1
```
Expected: `index:200`, `prd-en:200`, `plan-zh:200` (proves the publish-dir-relative `fetch()` paths still resolve).

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor: move docs site into site/ and set netlify publish=site"
```

---

### Task 2: Add the `agent/` Python skeleton with a smoke test

**Files:**
- Create: `agent/pyproject.toml`
- Create: `agent/src/jobpin_agent/__init__.py`
- Create: `agent/tests/test_smoke.py`
- Create: `agent/README.md`
- Create: `agent/THIRD_PARTY_NOTICES.md`
- Modify: `.gitignore` (Python entries)

**Interfaces:**
- Consumes: nothing.
- Produces: an importable package `jobpin_agent` exposing `__version__: str`. This is a placeholder home; real internal structure is Phase 0 of the Production Plan (out of scope here).

- [ ] **Step 1: Write the failing smoke test**

Create `agent/tests/test_smoke.py`:
```python
def test_package_imports_and_exposes_version():
    import jobpin_agent

    assert isinstance(jobpin_agent.__version__, str)
    assert jobpin_agent.__version__
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd agent && python -m pytest tests/test_smoke.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'jobpin_agent'` (package not created/installed yet).

- [ ] **Step 3: Create the package and project metadata**

Create `agent/src/jobpin_agent/__init__.py`:
```python
"""Jobpin Agent — local-first, AI-agent HR platform (product source).

Placeholder package. The real internal structure (Agent Core, Memory
Subsystem, sub-agents, Layer B orchestration) is Phase 0 of the Production
Plan — see ../site/plan/02-Production-Plan-EN.md.
"""

__version__ = "0.0.0"
```

Create `agent/pyproject.toml`:
```toml
[project]
name = "jobpin-agent"
version = "0.0.0"
description = "Jobpin Agent — local-first, AI-agent HR platform"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=8"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/jobpin_agent"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd agent && python -m pytest tests/test_smoke.py -v`
Expected: PASS (the `pythonpath = ["src"]` setting lets pytest import `jobpin_agent` without an install).

- [ ] **Step 5: Add the agent README and third-party notices stub**

Create `agent/README.md`:
```markdown
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
```

Create `agent/THIRD_PARTY_NOTICES.md`:
```markdown
# Third-Party Notices

## Hermes Agent (Nous Research) — MIT License

Portions of this product are **ported and adapted** from the Hermes Agent
(https://github.com/NousResearch/hermes-agent), used here under the MIT License.
The upstream source is vendored read-only as a git submodule at
`../reference/hermes/`.

Files derived from Hermes will be listed here as they are ported, e.g.:

- `src/jobpin_agent/memory/...`  ⟵ derived from `tools/memory_tool.py`
- `src/jobpin_agent/memory/...`  ⟵ derived from `agent/memory_provider.py`, `agent/memory_manager.py`
- `src/jobpin_agent/security/...` ⟵ derived from `threat_patterns.py`

(No files are ported yet. Keep the MIT copyright + license text below in any
substantial copied portion.)

---

MIT License

Copyright (c) 2025 Nous Research

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

> Note: confirm the exact upstream copyright line against `reference/hermes/LICENSE` once the submodule is added (Task 3); adjust the year/holder if it differs.

- [ ] **Step 6: Add Python ignores to `.gitignore`**

Append to `.gitignore`:
```gitignore

# Python (agent/)
__pycache__/
*.py[cod]
.venv/
venv/
.pytest_cache/
*.egg-info/
build/
dist/
```

- [ ] **Step 7: Commit**

```bash
git add agent .gitignore
git commit -m "feat: add agent/ python product skeleton with smoke test"
```

---

### Task 3: Add Hermes as a pinned submodule and rewrite the root README

**Files:**
- Create: `reference/hermes/` (git submodule)
- Create/Modify: `.gitmodules` (git-generated)
- Modify: `README.md` (monorepo overview)

**Interfaces:**
- Consumes: the `site/` and `agent/` trees from Tasks 1–2.
- Produces: a pinned `reference/hermes/` checkout for porting, and a README that documents the monorepo layout and the deploy boundary.

- [ ] **Step 1: Add the Hermes submodule**

Run:
```bash
git submodule add https://github.com/NousResearch/hermes-agent.git reference/hermes
```
Expected: clones into `reference/hermes/` and creates `.gitmodules`.

**If this fails (no network in this environment):** skip Steps 1–2, leave a note in the final summary with the exact command for the user to run later, and continue to Step 3. Do not block the restructure on network access.

- [ ] **Step 2: Verify the pin and that it sits outside the publish dir**

Run:
```bash
git submodule status
cat .gitmodules
test -f reference/hermes/LICENSE && echo "LICENSE present"
```
Expected: a pinned commit SHA for `reference/hermes`; `.gitmodules` points at the Hermes URL; `reference/` is not under `site/`. Cross-check the copyright line in `reference/hermes/LICENSE` against `agent/THIRD_PARTY_NOTICES.md`.

- [ ] **Step 3: Rewrite the root README as a monorepo overview**

Replace `README.md` with:
```markdown
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

Static, no build. Netlify config (`netlify.toml`) serves `site/` as the web
root. Run locally over HTTP (the viewer fetches markdown, which needs HTTP):

```bash
python -m http.server 8123 --directory site
# open http://localhost:8123/
```

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
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: add hermes submodule (porting reference) and monorepo README"
```

---

## Final verification (whole-plan gate, before handing back)

- [ ] `git ls-files | grep -E '^site/(index.html|assets/|plan/)'` shows the site under `site/`.
- [ ] `netlify.toml` contains `publish = "site"`.
- [ ] `cd agent && python -m pytest` passes.
- [ ] `reference/hermes/` is a pinned submodule outside `site/` (or, if network-blocked, the exact `git submodule add` command is reported to the user).
- [ ] Serving `site/` over HTTP returns 200 for `/`, `/plan/01-PRD-EN.md`, `/plan/02-Production-Plan.md`.
- [ ] **User-side gate (not automatable here):** open a Netlify deploy preview for `chore/wrap-docs-site`, confirm it matches production, then merge.

---

## Self-Review (author check)

**Spec coverage:** §4 layout → Tasks 1–3 produce it. §5 migration steps → Task 1 (moves + netlify), Task 2 (agent skeleton, .gitignore), Task 3 (submodule, README). §6 invariants → enforced by `publish=site` (Task 1) + submodule path (Task 3). §8 verification → Task 1 Step 4 + Final verification. §9 risks → Task 3 Step 1 network fallback. No gaps.

**Placeholder scan:** No "TBD/handle edge cases" placeholders; all file contents shown in full. The `THIRD_PARTY_NOTICES.md` "files derived…" list is intentionally illustrative (nothing ported yet) and labeled as such.

**Type consistency:** Only one symbol crosses tasks — `jobpin_agent.__version__: str`, defined in Task 2 Step 3 and asserted in Task 2 Step 1. Consistent.
