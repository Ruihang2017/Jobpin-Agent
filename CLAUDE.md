# CLAUDE.md — Jobpin Agent

Operating guide + handover for this repository. Read this first.

---

## 1. What this repo is

**Jobpin Agent** — a **local-first, AI-agent-driven HR platform** (resume matching, talent
search, recruitment, training, supervision/KPI), targeting the Australian market. It is built on a
**Hermes-derived agent kernel + memory subsystem** (ported from Nous Research's MIT-licensed Hermes
Agent), with provider-agnostic model backends.

This repository is a **monorepo** holding two things:

1. A **zero-build static docs site** (`site/`) that renders the PRD and Production Plan for
   reviewers. This is the **only** thing deployed to Netlify today.
2. The **actual product** source (`agent/`, Python) — currently a skeleton; real build starts at
   Production Plan **Phase 0**.

The canonical product documents live in `site/plan/` (they are both the spec and the content the
docs site displays):

| Document | English | 中文 |
|---|---|---|
| PRD | `site/plan/01-PRD-EN.md` | `site/plan/01-PRD.md` |
| Production Plan | `site/plan/02-Production-Plan-EN.md` | `site/plan/02-Production-Plan.md` |

---

## 2. Repository map & the deploy boundary

```
Jobpin-Agent/
├─ netlify.toml              # publish = "site"  (Netlify serves ONLY site/)
├─ README.md                 # monorepo overview
├─ CLAUDE.md                 # this file
├─ .gitignore                # OS cruft, .superpowers/, Python ignores
├─ .gitmodules               # pins the Hermes submodule
│
├─ site/                     # ← PUBLISHED. The docs viewer (zero build).
│   ├─ index.html
│   ├─ assets/  (app.js, render.js, feedback.js, style.css, vendor/{marked,highlight,github.css})
│   └─ plan/   (01-PRD*.md, 02-Production-Plan*.md)   ← canonical PRD/Plan, served at runtime
│
├─ agent/                    # ← NOT published. Python product (skeleton for now).
│   ├─ pyproject.toml        # py>=3.11, pytest; pythonpath=["src"]
│   ├─ src/jobpin_agent/__init__.py   # __version__ = "0.0.0"
│   ├─ tests/test_smoke.py
│   ├─ README.md
│   └─ THIRD_PARTY_NOTICES.md # MIT notice for code ported from Hermes
│
├─ reference/
│   └─ hermes/               # ← NOT published. Git submodule, pinned. PORTING REFERENCE ONLY.
│
└─ docs/superpowers/         # ← NOT published. Internal specs + plans.
    ├─ specs/   (design specs)
    └─ plans/   (implementation plans)
```

**The single most important invariant:** Netlify (`netlify.toml`) has `publish = "site"` and an
empty build command. **Only `site/` is public.** `agent/`, `reference/hermes/`, and
`docs/superpowers/` are never served. Do **not** move product code into `site/`, and do **not**
revert `publish` to `"."` (that would re-expose all source + internal docs on the live URL).

The docs viewer renders markdown at runtime: `assets/app.js` `fetch()`es `plan/<doc>.md` relative
to the web root. Because Netlify serves `site/` as root, those paths resolve and **public URLs are
unchanged** from before the restructure (`/`, `/plan/01-PRD-EN.md`, …).

---

## 3. How to work here

**Run the docs site locally** (needs HTTP — the runtime `fetch()` won't work over `file://`):
```bash
python -m http.server 8123 --directory site
# open http://localhost:8123/
```

**Run the product tests:**
```bash
cd agent && python -m pytest        # currently: 1 passing smoke test
```

**Populate the Hermes reference** (after a fresh clone):
```bash
git submodule update --init --recursive   # fills reference/hermes/
```

**Editing docs content:** edit the markdown in `site/plan/` and redeploy — no build, no duplicate
copies. Keep the EN and 中文 versions in sync (each change goes into both `*-EN.md` and the
matching Chinese file).

---

## 4. HANDOVER — what was done and why (changes to date)

Two work sessions on branch **`chore/wrap-docs-site`** (off `main`). `main` auto-deploys to
Netlify, so all structural work was branched and is **not yet merged**.

### Session A — repo restructure (wrap the docs site, open the product home)

**Goal:** build the real product in-repo without disturbing the live docs deployment, and bring in
Hermes as porting reference. Driven by `docs/superpowers/specs/2026-06-26-wrap-docs-site-design.md`
and `docs/superpowers/plans/2026-06-26-wrap-docs-site.md`.

1. **Moved the docs site into `site/`** (`git mv` — history preserved):
   `index.html`, `assets/`, `plan/` → `site/…`. Then changed `netlify.toml`
   `publish = "."` → `publish = "site"`. Net effect: identical public output and URLs, but now only
   `site/` is published. *Side benefit:* `docs/superpowers/` (internal plans) and all product source
   are no longer reachable on the live site, which they were under `publish = "."`.
   *Verified:* served `site/` over HTTP — `/`, all four `plan/*.md`, `assets/app.js`, and vendor
   files returned 200.

2. **Added the `agent/` Python skeleton** (TDD): a `jobpin_agent` package (`src/` layout) exposing
   `__version__`, a `pyproject.toml` (py≥3.11, pytest with `pythonpath=["src"]` so tests run without
   an install), a passing smoke test, `agent/README.md`, and `agent/THIRD_PARTY_NOTICES.md` (MIT
   notice stub for Hermes-derived code). Added Python entries to `.gitignore`. The internal
   structure (Agent Core, Memory Subsystem, sub-agents, Layer B orchestration) is **intentionally
   not built** — that is Phase 0.

3. **Added Hermes as a pinned git submodule** at `reference/hermes/`
   (`https://github.com/NousResearch/hermes-agent.git`, pinned at `e3db1ef`,
   tag `v2026.6.19-839-ge3db1ef92`). It sits outside `site/` (never published) and is a
   **read-only porting reference, never a runtime dependency**. *Verified:* the files the Production
   Plan cites for porting all exist in the checkout — `tools/memory_tool.py`,
   `agent/memory_provider.py`, `agent/memory_manager.py`, `tools/threat_patterns.py`,
   `agent/conversation_loop.py`, `agent/conversation_compression.py`. The upstream `LICENSE`
   copyright ("Copyright (c) 2025 Nous Research") matches the notices stub. Rewrote root `README.md`
   as a monorepo overview.

### Session B — multi-provider AI strategy in the docs (+ this CLAUDE.md)

4. **Added explicit AI-provider selection to all four product docs.** The docs already described
   "provider-agnostic + local-default + optional cloud + BYO-key + APP 8" but never named the
   providers. Added — in **PRD §11.3** and **Production Plan §1.11**, EN and 中文 in parallel:
   - **Launch set: OpenAI, Anthropic Claude, DeepSeek** (+ the local-model path).
   - **OpenAI is the first implemented adapter and the default for the internal pilot / development**
     (an account already exists). Claude and DeepSeek adapters are built to interface parity and
     enabled by supplying a key (BYO-key), **no code change**.
   - **Local-first remains the commercial default** (PRD §1, §7, G7). Any cloud provider routes PII
     outbound → invokes the existing explicit-enablement + de-identification + APP 8 controls; only
     "fully local" mode avoids cross-border disclosure.
   - Production Plan §1.11 gained deliverables `ai/providers` (the `ModelProvider` interface + OpenAI
     adapter + key-gated Claude/DeepSeek adapters + selection/BYO-key config) and
     `ai/providers/conformance` (a provider-conformance test), plus an exit criterion: switch among
     OpenAI/Claude/DeepSeek/local via config + key with no code change.

5. **Created this `CLAUDE.md`.**

### Commit log on `chore/wrap-docs-site` (newest last)

```
d3a2be7  docs: design spec for wrapping docs site + opening agent/ product home
0cba78b  docs: implementation plan for wrapping docs site + agent/ home
6a83e31  refactor: move docs site into site/ and set netlify publish=site
8677888  feat: add agent/ python product skeleton with smoke test
4673aba  chore: add hermes submodule (porting reference) and monorepo README
(+ pending) docs: name OpenAI/Claude/DeepSeek providers in PRD & Plan; add CLAUDE.md
```

---

## 5. Workflow convention — automated superpowers flow (single-agent)

**We use the Superpowers workflow as the main approach.** For feature/change work the order is:
**brainstorming → spec → writing-plans → execution**, with specs in
`docs/superpowers/specs/` and plans in `docs/superpowers/plans/`.

**Automation (sanctioned by the repo owner — overrides the skills' intermediate HITL gates):**
Once the **user has approved the design** at the end of brainstorming, **proceed automatically and
without pausing** through:

> write spec → **self-review spec** → write plan → **self-review plan** → **execute (single-agent,
> inline)**

Do **not** stop to ask the user to review the spec, and do **not** ask "which execution approach?"
— default to **single-agent inline execution** (`superpowers:executing-plans`), not subagent
fan-out, unless the user asks otherwise. The self-review steps still run (and are the quality gate);
the spec and plan are still written and committed. We are **automating the wait-for-user gates the
owner would not read anyway**, not skipping the steps.

**Gates that are KEPT (still require the user):**
- The **design / approach approval** in brainstorming (the creative decision the owner does review).
- Anything **irreversible or outward-facing**: `git push`, merging to `main`, triggering a
  **Netlify deploy**, deleting/overwriting files not created this session, sending data to external
  services. Confirm these before acting.

This convention lives here because CLAUDE.md instructions take precedence over default skill
behavior (user instructions > skills > system default).

---

## 6. Documentation currency (keep docs in sync — required)

Docs are part of a change, not an afterthought. In the **same commit/PR** as the change that makes
them stale:

- **READMEs** — update `README.md` (root, the monorepo map) and/or `agent/README.md` (product dev
  quickstart) whenever structure, commands, layout, or the deploy boundary change.
- **PRD + Production Plan** (`site/plan/01-PRD*.md`, `02-Production-Plan*.md`) — update whenever
  product scope, architecture, a recorded decision, or an acceptance measure changes. **Always edit
  EN and 中文 together** (`*-EN.md` and the matching Chinese file) so they stay in lockstep.
- **`agent/THIRD_PARTY_NOTICES.md`** — update whenever a file is ported from Hermes (Tenet 1 of
  `TEXTBOOK_SPEC.md`).
- **This file** — reflect finished work in §4 (handover) / §7 (status), and the PRD §0 status if the
  project phase changed.

Rule of thumb: if a reader following the docs would be misled after your change, the docs are part
of the change — a PR that alters behaviour/structure without the matching doc update is incomplete.

> Optional hard enforcement: a Stop hook can remind to check doc currency before finishing — ask to
> have it wired into `settings.json` if you want it enforced rather than conventional.

---

## 7. Product decisions & constraints to respect

- **Local-first by default** (commercial product): agent runtime, memory, and HR data run/stored on
  the customer's premises; PII does not leave by default. Outbound calls are optional, disableable,
  de-identified, APP 8-governed.
- **Own the backbone:** the agent kernel + memory subsystem are **ported from Hermes**, not depended
  on at runtime. Never `pip install` Hermes or build the product on it. When porting a file, copy it
  into `agent/`, adapt it, and **record it in `agent/THIRD_PARTY_NOTICES.md`** (keep the MIT
  copyright + license text in substantial copied portions — PRD §2.7). Ported code gets its **own**
  security review.
- **Provider-agnostic models:** OpenAI (first/default for pilot), Claude, DeepSeek, + local — behind
  one `ModelProvider` interface; swap by config + key. See PRD §11.3 / Plan §1.11.
- **Compliance is first-class** (Australia only, pilot): HITL on individual-affecting decisions,
  explainability, audit, bias hygiene, memory governance (PRD §9.5, §11.5). Don't introduce
  intrusive monitoring (PRD N4) or fully-automated hire/fire (N1).
- **MVP discipline / YAGNI:** the Production Plan defers multi-tenancy, full event sourcing,
  `CompositeMemoryProvider` multi-provider merging, and heavy orchestration engines until their
  trigger signals. Keep the abstraction; don't build ahead.

---

## 8. Current status & next steps

**Status:** restructure + provider-doc updates complete on `chore/wrap-docs-site`; **nothing merged
to `main`; production untouched.** `agent/` is an empty skeleton.

**Immediate next steps:**
1. **Land the restructure:** push `chore/wrap-docs-site`, open the Netlify **deploy preview**,
   confirm it matches production, then merge to `main`. (Owner action — involves push/deploy/merge.)
2. **Start the product — Production Plan Phase 0:** the thin end-to-end slice + the Hermes memory
   port (`memory_tool.py` → `memory_provider.py`/`memory_manager.py`, `threat_patterns.py`). This is
   substantial and gets its own brainstorm → spec → plan cycle. The first concrete provider work is
   the §1.11 `ai/providers` adapter layer with the OpenAI adapter.
