# Design: Phase 0 · Thin hiring vertical slice with a real LLM (pulls §1.15 forward)

| Item | Value |
|---|---|
| Date | 2026-06-29 |
| Status | Approved (brainstorming output) |
| Point | A thin end-to-end vertical slice — pulls Production Plan **§1.15** forward (partial); reorders the plan |
| Related | Plan §1.15 (thin slice), §1.1 (loop + OpenAIProvider + .env), §1.3 (manager/hooks), §1.4 (candidate/semantic memory), §1.11 (AI layer — embedder/router, mostly deferred); PRD §1, §7 (local-first), §11.3, M1 |
| Build strategy | New code wiring existing pieces + one real-embedder adapter; real-LLM path opt-in |

## 1. Goal

Make the system **actually do HR work with a real model**, end-to-end: ingest a few (synthetic, plain-text)
résumés into the §1.4 candidate memory, ask a hiring question, and have a **real OpenAI model** recall the
right candidates (semantically) and return an **explainable shortlist with grounded citations** under
**HITL framing** — proving the whole stack (memory → manager → hooks → loop → real model) connects. This
is the plan's "thin vertical slice first — prove the pipe is connected, then pour water in" (§0), pulled
forward from §1.15.

## 2. Scope

**In:**
- A **real embedder** behind the existing `EmbedFn` seam — `openai_embedder` (OpenAI
  `text-embedding-3-small`), so recall is **semantic** not lexical (directly addresses "the vector store
  doesn't pull weight"). Lazy client (no network at construction); opt-in (needs a key). The
  `hashing_embedder` stays the offline default.
- A **hiring-slice builder** + runnable demo (`examples/hiring_slice_demo.py`): ingest synthetic résumés
  into a `CandidateMemoryProvider` + an org rubric into a `SemanticRAGProvider`, wrap in the §1.4
  `CompositeMemoryProvider`, drive it through the §1.3 `MemoryManager` + `MemoryManagerHooks`, attach to a
  §1.1 `Agent`. Real `OpenAIProvider` when a key is present; `FakeProvider` + `hashing_embedder` offline.
- An **HR system prompt** (`SystemPromptParts`: org policy / compliance-HITL / role permissions) framing
  the agent as a recommend-only, evidence-grounded, no-protected-attributes hiring assistant.
- **Deterministic wiring tests** (fake model + fake embedder) + **one opt-in real-OpenAI integration test**
  (skipped without a key — matching the existing `test_openai_provider` pattern).
- A **Plan §1.15 pull-forward note** (EN+中文) recording the reorder + what's stubbed.

**Out / deferred behind the seams already built (it is a thin slice, NOT a real decision — Phase 0
"ships no functionality facing real decisions"):**
- Governance §1.5 (pass-through `write_gate`/`scope_filter`); injection scan §1.6 (pass-through `scan_entry`).
- Résumé **parsing** (PDF/Word) → §1.11/§1.15; the slice uses plain-text résumés.
- A real **HITL workflow engine** (Layer B §1.7) → here it's prompt framing only.
- The **model router / fallback / de-identification / eval / tracing backend** (§1.11) → the slice uses the
  §1.1 `OpenAIProvider` directly + the §1.1 `Tracer`.
- A numeric **matching/scoring** algorithm + match tools → Phase 1 M1; here the LLM explains, grounded in recall.

**Privacy:** the demo uses **synthetic résumés only** (no real candidate PII). Real PII to a cloud model
needs the de-identification pipeline (§1.11), which is not built — stated in the demo + devlog. Local-first
default is unchanged (PRD §1/§7/G7); this is an opt-in dev/pilot path using the operator's own key (BYO-key).

## 3. Components

- `memory/embedding.py` — add **`openai_embedder(model="text-embedding-3-small", api_key=None, client=None) -> EmbedFn`**
  (lazy OpenAI client; one `embeddings.create` per call) + keep `hashing_embedder` the default. The
  production embedder *selection/config* remains §1.11/§1.4-real; this is the real option behind the seam.
- `examples/hiring_slice_demo.py` — `build_hiring_slice(*, embed_fn, embed_version, model) -> (agent, store, sid, manager, hooks)`
  (injectable for tests) + `run(question, *, embed_fn, embed_version, model) -> dict` + `main()` (picks
  real-vs-fake by key presence) + the synthetic résumé fixtures + the HR `SystemPromptParts`.
- `agent/tests/test_hiring_slice.py` — deterministic wiring tests (fake model + `hashing_embedder`).
- `agent/tests/test_openai_embedder_optin.py` (or fold into the slice test) — opt-in real-OpenAI test
  (skipped without `OPENAI_API_KEY`): real embedder recalls + real model answers, mentioning a candidate.

## 4. How a turn flows (no new tools — recall is automatic)

`run_turn(question)` → the §1.3 `MemoryManagerHooks.prefetch` recalls candidates+rubric (semantic NN over
the vector store, scoped) → the §1.1 loop fences it as a `<memory-context>` message → the **real model**
reads the HR system prompt + the fenced recall and answers with an explainable, **cited** shortlist. No HR
tools are registered; the agent reasons over recalled memory. (Match-scoring tools are M1.)

## 5. Testing & acceptance

- **Deterministic (CI, fake model + fake embedder):** ingest 3 synthetic résumés → `run_turn` → assert the
  composed prompt the model received contains (a) the HR/HITL system-prompt framing, (b) the recalled
  candidate(s) + `[memory_key | source]` citation in a `<memory-context>` message. Proves the wiring closes
  end-to-end with no `agent_loop.py` change.
- **`openai_embedder` offline:** asserting it constructs lazily (returns a callable) without a key/network.
- **Opt-in real (skipped without a key; NOT run in CI / not run by the author — it spends the user's
  money):** real embedder + real `gpt-4o-mini` → the answer is non-empty and names a fitting candidate.
- **Acceptance (the slice's bar):** running `python examples/hiring_slice_demo.py` with a key produces a
  grounded, HITL-framed shortlist citing the recalled résumé evidence — the first end-to-end real-model HR result.

## 6. Triple-review, documentation

- **Triple-review** (senior engineer / architect / PM) vs the plan + this design; fix the Plan first if wrong.
- **Bilingual devlog** to `CLAUDE.md` §6 standard (files table, the `openai_embedder` signature, the HR
  prompt verbatim, the turn-flow diagram, the test matrix, the honest "real-model/PII/parsing deferred"
  caveats, what the review changed). Plan §1.15 note (EN+中文); `CLAUDE.md` §8 status.

## 7. Risks

- **Non-determinism / cost of the real model** — mitigated: deterministic wiring is fake-model tested; the
  real path is opt-in and never run unsolicited.
- **Reordering the plan** — mitigated: it's a thin, non-decision slice (plan §0 endorses slice-first); the
  reorder + stubs are recorded in Plan §1.15 (EN+中文).
- **Coupling memory→OpenAI** via `openai_embedder` — mitigated: lazy import, behind the `EmbedFn` seam,
  default stays stdlib; documented as the real option, not the default.
- **PII to cloud** — mitigated: synthetic résumés only; de-id (§1.11) is the gate for real PII; stated plainly.
