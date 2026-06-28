# CLAUDE.md — `agent/` (Jobpin Agent product source)

Scoped guide for developing the **product** in this directory. The **root `../CLAUDE.md` also
applies** (repo map, deploy boundary, the automated single-agent workflow convention, the
documentation-currency contract). This file adds the rules that govern Python/agent work here.

Authoritative product docs: **PRD** `../site/plan/01-PRD-EN.md` and **Production Plan**
`../site/plan/02-Production-Plan-EN.md` (中文: `01-PRD.md` / `02-Production-Plan.md`). The
engineering quality bar is `../TEXTBOOK_SPEC.md` — **read it before porting anything.**

**Reflect against the whole plan before each point or feature change.** Re-read the relevant PRD
sections **and the entire Production Plan** before starting a point or altering a feature — a point's
scope and sequencing come from the *full* plan (the §1.x dependency order, the Plan §1.0 Key
Invariants, the PRD §13.1 deferrals + their trigger signals), not from one paragraph read in
isolation. See root `../CLAUDE.md` §5 ("Context-first") for the rule and the §1.3 lesson behind it.

---

## What we are building

A local-first, stateful, memory-driven, auditable **multi-agent** HR system on a **Hermes-derived
agent kernel + memory subsystem**. Not a chatbot: perceive → plan → act → remember, under human
supervision. The moat is per-customer **organisational memory** + built-in Australian compliance +
full-lifecycle workflow depth.

---

## Non-negotiable development rules

### 1. Own the backbone — port, don't depend
- **Never** add Hermes as a runtime dependency (`pip install`), and **never** import from
  `../reference/hermes/` at runtime. That checkout is a **read-only porting reference**.
- To use a Hermes capability you **port** it: copy the relevant file into `src/jobpin_agent/`, adapt
  it, and own it thereafter.
- The Hermes kernel solves "single agent inference + memory" (Layer A). The hiring process is a
  cross-day, multi-party, resumable business process (Layer B) — that's **net-new** orchestration we
  build, not something Hermes gives us (PRD §2.6).

### 2. Porting discipline (enforced by `../TEXTBOOK_SPEC.md`)
When you port a Hermes mechanism:
- **Name the real upstream file + symbol** in code comments and the commit (e.g. `MemoryStore` in
  `tools/memory_tool.py`, `MemoryProvider` in `agent/memory_provider.py`, `MemoryManager` in
  `agent/memory_manager.py`, threat patterns in `tools/threat_patterns.py`).
- State **what changed after the port and why** (local-first, HR governance, trimmed for clean
  ownership, etc.).
- **Record it in `THIRD_PARTY_NOTICES.md`** (keep the MIT copyright + license text — PRD §2.7).
- Ported code gets its **own security review** — MIT is "as is"; a regulated product must not blindly
  trust upstream. Also verify the licences of any transitive deps the ported module pulls in.

What to port vs rewrite (PRD §2.7):
| Hermes component | Strategy |
|---|---|
| Memory subsystem (`memory_tool.py` / `memory_provider.py` / `memory_manager.py`) | **Port the code** |
| Injection defence (`threat_patterns.py`, streaming scrubber) | **Port the code** |
| Conversation loop (`conversation_loop.py`, `conversation_compression.py`) | **Borrow design, rewrite trimmed** |
| gateway / CLI / TUI / multi-provider pipeline | **Do not take; build as needed** |

### 3. Memory invariants (inherited from Hermes; do not break)
- **System-prompt frozen snapshot**: generated once at load, never changes during a session (keeps
  the prompt-cache prefix stable). The active memory state is what tool calls mutate.
- **Atomic writes + file lock + drift detection**: temp file → fsync → `os.replace`; exclusive lock
  on a separate `.lock`; reject writes that can't round-trip (suspected external edit), backing up
  `.bak` first.
- **`<memory-context>` fenced injection + threat scan** on any external text (resumes/emails are a
  real injection vector) before it enters memory/context.
- **Sub-agents `skip_memory`**: sub-agents do not write sensitive memory directly; the **parent agent
  vets and writes** after observing their output.
- **Reject invalid writes**: memory writes must carry provenance + lawfulness labels; unlabeled
  writes are rejected (PRD §9.5/§9.6).
- The compression `on_pre_compress` hook return value is **discarded by Hermes mainline** — Jobpin
  **must wire it up itself** (inject key facts into the summary). This is net-new (PRD §8.3, §9.1).

### 4. Local-first & privacy
- Default: agent runtime, memory, HR data run/stored locally; PII does not leave the machine.
- **No PII goes outbound without the de-identification pipeline** (detect → mask/pseudonymise →
  record mapping locally). This is a precondition for APP 8, not optional.
- Encrypt local DB + memory files at rest; append-only local audit log.

### 5. Models / providers (PRD §11.3, Plan §1.11)
- One `ModelProvider` interface; one adapter per backend. **OpenAI is the first adapter and the
  default for the internal pilot/dev** (account exists). **Anthropic Claude** and **DeepSeek**
  adapters are built to the same interface and **key-gated** (enabled by config + BYO-key, no code
  change). Local-model path stays the commercial default.
- New providers must pass the **provider-conformance test** (`ai/providers/conformance`) — the same
  task routes/works across any configured provider.
- API keys (incl. customer BYO-key) live in the OS keystore/secret store, never in code or git.

### 6. Compliance & responsible AI (Australia; PRD §11.5)
- Any recommendation affecting an individual → **HITL review entry + explainable rationale + audit
  record**. No fully-automated hire/fire (N1). No intrusive monitoring (N4).
- **Bias hygiene**: never store/use protected attributes (or proxy variables) as decision features;
  scan for proxies; bias-audit monitoring on calibration writes.

### 7. MVP discipline (YAGNI — follow the Plan's deferrals)
Deferred until their trigger signal fires: multi-tenancy, full event sourcing,
`CompositeMemoryProvider` multi-provider merging (Phase 2 / M4), heavy orchestration engines
(Temporal/LangGraph — only if Layer B genuinely needs one). **Keep the abstraction; don't build
ahead.**

### 8. TDD + acceptance measures
- Write the failing test first; minimal code to pass; commit in small steps (`python -m pytest` from
  `agent/`).
- **Every deliverable needs a testable acceptance measure** ("How to verify this yourself") — a
  deliverable with no acceptance measure is not a deliverable (`../TEXTBOOK_SPEC.md`).

---

## Target package layout (grows with the Production Plan; do not scaffold ahead)

```
src/jobpin_agent/
├─ core/           # Layer A kernel: conversation loop, system-prompt assembly, tool registry, delegation
├─ memory/         # store, provider (ABC), manager, vector, providers/, fence  ← Hermes port + HR governance
├─ governance/     # namespaces, provenance/lawfulness labels, TTL, RBAC, audit, de-bias
├─ security/       # injection defence (threat_patterns port), guardrails, secrets
├─ orchestration/  # Layer B: hiring-loop state machine (self-built → Temporal if needed)
├─ data/           # local relational store, embedded vector store, append-only audit log
├─ integration/    # MCP tools + connectors (ATS/HRIS/calendar/email), anti-corruption layer
├─ ai/             # router, deid, prompts, providers/ (openai, anthropic, deepseek), providers/conformance
├─ eval/           # offline eval harness (quality + fairness scaffold)
└─ obs/            # step-level tracing (Langfuse / OTel, prefer local)
```
(Today only the placeholder package exists. Each module lands in its Production-Plan phase/workstream.)

---

## Documentation currency (this directory)

When you change `agent/`, update **in the same change**: `agent/README.md` (if commands/structure
changed) and `agent/THIRD_PARTY_NOTICES.md` (whenever you port a file). If a change alters product
scope or a recorded decision, also update the PRD + Production Plan (both EN and 中文) per the
contract in `../CLAUDE.md`. See root `../CLAUDE.md` for the full documentation-currency rule.

### Bilingual docstrings (required here)

Every Python file, class, and function under `agent/` — **including tests and `__init__.py`** —
carries a **comprehensive docstring in English then 中文**, with `Args:`/`Returns:` (plus `Raises:`
and a short learning note where useful). The code is a study reference, so explain the *why*, not
just the *what*. Format: English block → blank line → parallel 中文 block. Canonical example:
`src/jobpin_agent/core/system_prompt.py`. Keep both languages in sync when a signature/behaviour
changes; never let a docstring contain `"""`.

### Per-folder `README.md`

Every folder under `agent/` (src, jobpin_agent, core, model, tests, tests/data, examples) has a
bilingual `README.md` (English section, then 中文 section) describing each file and subfolder. Update
it whenever files are added/renamed/removed. This is the repo-wide convention (see root `../CLAUDE.md`
§6).
