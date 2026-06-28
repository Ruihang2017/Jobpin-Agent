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

### Session C — Phase 0 §1.1 Agent Core (branch `phase0/1.1-agent-core`, off `chore/wrap-docs-site`)

First product point built end-to-end through the per-point cycle (§5). Added `agent/CLAUDE.md`
(scoped dev guide), `TEXTBOOK_SPEC.md` (resolved a dangling Plan reference), and the §6 doc-currency
contract; refreshed the PRD §0 status (EN+中文).

6. **Implemented the Agent Core (Layer A)** — `agent/src/jobpin_agent/core/`: provider-agnostic
   message/tool types, `ModelProvider` ABC + `FakeProvider` + minimal `OpenAIProvider` (all wire
   mapping isolated), deterministic system-prompt assembler (golden snapshot), step-level tracer,
   `MemoryHooks`/`NoOpHooks` seam, SQLite session store (branch/reset), the synchronous turn loop
   (4 paths), and `delegate()` (skip_memory + parent observation). Spec + plan in
   `docs/superpowers/{specs,plans}/2026-06-27-p0-1.1-agent-core*`.
7. **Triple-reviewed** (senior engineer / architect / PM). Key fix: per-turn `prefetch` recall is a
   fenced `<memory-context>` **message**, not the frozen system-prompt snapshot slot (keeps the
   prefix stable; lets §1.2–1.6 attach without a loop refactor). Also added `session_id` to
   `prefetch`, delegation lineage + parent context, and corrected Plan §1.1's compression wording
   (the seam is here; wiring is §1.6) **before** finalizing.
8. **Tests:** `python -m pytest agent` → **24 passed, 1 skipped** (opt-in OpenAI integration). Demo
   runs offline. Bilingual study devlog at `site/devlog/p0-1.1-agent-core{,-EN}.md`.

Known intentional gap: `config.db_path` / `max_tool_iterations` aren't wired to a composition root
yet (no real app entry point until later). Next point: **§1.2** (file-backed `MemoryStore` port).

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

## 5. Workflow convention — automated superpowers cycle (single-agent, one point at a time)

**We use the Superpowers workflow as the main approach**, working **one small Production-Plan point
per cycle** (the smallest workstream sub-item — e.g. §1.1 Agent Core; never bundle points). For each
point the full cycle is:

> **brainstorm → spec → writing-plans → execute → test → triple-review → document**

with specs in `docs/superpowers/specs/` and plans in `docs/superpowers/plans/`.

**Context-first — reflect against the WHOLE PRD + Production Plan before each point or feature
change (required).** Before brainstorming a new point, or changing any existing feature, re-read the
relevant PRD sections (`site/plan/01-PRD-EN.md`) **and the entire Production Plan**
(`site/plan/02-Production-Plan-EN.md`), and decide scope by where the work sits in the *whole* plan —
not by its own paragraph. Specifically weigh: the **§1.x dependency order** (what the next points
need), the **Key Invariants** (Plan §1.0) and compliance constraints (PRD §9.5/§11.5), and the
**deferred items + their trigger signals** (PRD §13.1) so you neither build ahead nor invert the
order. *Lesson that motivated this rule:* the §1.3 memory-write-tool scope **flipped** once the full
PRD + Plan were read — the governed write-gate is literally the next point (§1.5), so a model-facing
write tool belongs there, not in §1.3. Reading one section in isolation would have got it backwards.

**Automation (sanctioned by the repo owner — overrides the skills' intermediate HITL gates):** once
the **user has approved the design** for a point, **proceed automatically and without pausing**
through: write spec → self-review spec → write plan → self-review plan → execute (single-agent,
inline) → test → triple-review → document. Default to **single-agent inline execution**
(`superpowers:executing-plans`), not subagent fan-out, for the *implementation*. The self-review
steps still run; spec and plan are still written and committed. We automate the **wait-for-user
review gates**, not the steps themselves.

**Exceptions ALWAYS kept (still pause / require input):**
- **Clarifying questions** — still ask them whenever a genuine ambiguity would change the work.
  Automation removes the wait-for-review gates, **not** the right to ask. (Brainstorming always
  involves clarifying questions before the design.)
- **Design / approach approval** in brainstorming (the creative decision the owner reviews).
- **Irreversible or outward-facing actions**: `git push`, merging to `main`, triggering a Netlify
  deploy, deleting/overwriting files not created this session, sending data to external services.
  Confirm before acting.

**After implementing each point — test, then triple-review against the Production Plan:**
1. **Test** the point against its acceptance measures (`TEXTBOOK_SPEC.md`).
2. **Review from three independent perspectives** (e.g. three focused review subagents): **senior
   engineer** (correctness, quality, test design), **architect** (boundaries, fit with the
   Hermes-derived design and the §1.x dependency order), **product manager** (does it match PRD/Plan
   intent + acceptance criteria). Each confirms the point is **in line with the Production Plan**.
3. **If a review finds the Production Plan (or PRD) itself is wrong**, fix the doc **first** —
   bilingually (EN + 中文, per §6), leaving the rationale — **then** implement against the corrected
   plan. The Plan is the source of truth, but it is correctable; never quietly diverge from it.

**Document every implemented point as a bilingual study reference** (see §6).

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
- **This file** — reflect finished work in §4 (handover) / §8 (status), and the PRD §0 status if the
  project phase changed.
- **Per-point study reference (`site/devlog/`)** — every implemented Production-Plan point gets a
  teaching write-up explaining **how it was implemented and why**, in **EN + 中文**
  (`p<phase>-<point>-<slug>-EN.md` + the Chinese base name `p<phase>-<point>-<slug>.md`), so the repo
  doubles as a study reference. These live under `site/` (served docs); wiring them into the viewer's
  navigation is an optional follow-up.
- **Bilingual docstrings (`agent/`)** — every Python file, class, and function under `agent/`
  (including tests and `__init__.py`) carries a **comprehensive docstring, English then 中文**, with
  `Args:`/`Returns:` (and `Raises:`/learning note where useful). The code is a study reference; keep
  both languages in sync whenever a signature or behaviour changes. Format: an English block, a blank
  line, then a parallel 中文 block (see `agent/src/jobpin_agent/core/system_prompt.py` for the canonical
  shape). Never let a docstring contain `"""`.
- **Per-folder guide (`README.md`)** — every meaningful folder repo-wide has a bilingual `README.md`
  (English section, then 中文 section) listing what each file and subfolder does. Update it when you
  add/rename/remove files in that folder. Excludes the `reference/hermes` submodule internals and
  `site/assets/vendor/` (third-party). Folders that already have a README (root, `agent/`) carry the
  manifest as a **Contents / 目录** section inside their existing README.

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

**Status:**
- Restructure + **§1.1 Agent Core: merged to `main`** (two PRs). `main` holds the full §1.1 + the
  .env / chat / observability / docs follow-ons.
- Phase 0 **§1.2 file-backed `MemoryStore`: complete** on `phase0/1.2-memory-store` (off `main`);
  triple-reviewed (port confirmed **faithful**); security review (`docs/security/p0-1.2-…`) +
  bilingual devlog written. **Not merged.**
- Phase 0 **§1.3 `MemoryProvider` + `MemoryManager` + fence + seam: complete** on
  `phase0/1.3-memory-provider-manager` (off `phase0/1.2-memory-store`); **70 tests pass, 1 skipped**;
  triple-reviewed (all three **YES**, port **faithful**, "no `agent_loop.py` change" git-verified);
  Plan corrected (EN+中文) per the review; security review (`docs/security/p0-1.3-…`) + bilingual
  devlog written. **Not merged.** The agent's system prompt now carries Org/Recruiter memory through
  the seam with no loop change; the governed model-facing **write tool is deferred to §1.5**.

**Branch:** `phase0/1.3-memory-provider-manager` (off `phase0/1.2-memory-store`, off `main`). Merge
order: **§1.2 → §1.3**.

**Immediate next steps:**
1. **Land §1.2 then §1.3:** owner merges `phase0/1.2-memory-store` → `main`, then
   `phase0/1.3-memory-provider-manager` → `main` (kept gate; auto-deploys Netlify).
2. **Next point — §1.4 or §1.5:** §1.4 = embedded vector store + Candidate/Semantic providers behind
   the §1.3 `MemoryProvider` interface (mind the §1.4 ↔ Phase-2 single-external reconciliation flagged
   in Plan §1.3); §1.5 = HR memory governance — the write-gate **and** the model-facing `memory` write
   tool, born governed. Same per-point cycle (§5).
