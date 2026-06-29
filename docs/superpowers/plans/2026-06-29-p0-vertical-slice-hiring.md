# Thin hiring vertical slice (real LLM) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (single-agent inline, `CLAUDE.md` §5).

**Goal:** Ingest synthetic résumés → a real OpenAI model recalls the right candidates (semantically) and returns an explainable, cited, HITL-framed shortlist — end-to-end, no `agent_loop.py` change.

**Architecture:** Wire existing pieces (§1.1 loop+OpenAIProvider, §1.3 manager/hooks, §1.4 candidate/semantic/composite) + one real-embedder adapter behind the `EmbedFn` seam. Real-LLM path opt-in; offline path uses the fake model + fake embedder.

**Tech Stack:** Python ≥3.11; the existing `openai` dep (lazy); pytest. No new deps.

## Global Constraints
- **Bilingual docstrings** (EN then 中文) on every new function/file incl. tests; never `"""` inside a docstring.
- **Real-LLM path is opt-in.** Deterministic wiring tested with `FakeProvider` + `hashing_embedder`; the real-OpenAI test is **skipped without `OPENAI_API_KEY`** and **must NOT be run by the author** (it spends the user's money). Synthetic résumés only (no real PII).
- **No `agent_loop.py` / core change.** Attach only through the §1.3 hooks + §1.1 `SystemPromptParts`.
- **Seams stay stubbed** (governance §1.5 / scan §1.6 = pass-through); no new HR tools (recall is automatic via the prefetch hook).
- Run from `agent/`: `python -m pytest`. Commit per task.

## File Structure
- Modify `memory/embedding.py` — add `openai_embedder(...)`.
- Create `examples/hiring_slice_demo.py` — `build_hiring_slice`, `run`, `main`, synthetic fixtures, HR prompt.
- Create `agent/tests/test_hiring_slice.py` — deterministic wiring tests + `openai_embedder` lazy test + opt-in real test.

---

### Task 1: `openai_embedder` (real semantic embedder behind `EmbedFn`)
**Files:** Modify `memory/embedding.py`; test in `test_hiring_slice.py`.
**Produces:** `openai_embedder(model="text-embedding-3-small", api_key=None, client=None) -> EmbedFn`.

- [ ] **Step 1 — test (offline, no network):** `from jobpin_agent.memory.embedding import openai_embedder`; `e = openai_embedder()`; assert `callable(e)` (constructs lazily — no client built, no network, no key needed). Optionally: inject a fake client with `.embeddings.create(...)` returning an object whose `.data[0].embedding == [0.1,0.2,0.3]`, assert `e("hi") == [0.1,0.2,0.3]`.
- [ ] **Step 2 — run, expect fail** (ImportError).
- [ ] **Step 3 — implement** in `embedding.py`:
```python
def openai_embedder(model="text-embedding-3-small", api_key=None, client=None) -> EmbedFn:
    state = {"client": client}
    def embed(text: str) -> list[float]:
        c = state["client"]
        if c is None:
            from openai import OpenAI
            c = state["client"] = OpenAI(api_key=api_key)
        return list(c.embeddings.create(model=model, input=text).data[0].embedding)
    return embed
```
  Bilingual docstring: real semantic option behind `EmbedFn`; lazy client; opt-in; not the default; production selection/config = §1.11.
- [ ] **Step 4 — run, expect pass** (with the injected-fake-client assertion).
- [ ] **Step 5 — commit** `feat(memory): openai_embedder — real semantic embedder behind the EmbedFn seam (opt-in)`.

### Task 2: the hiring slice (builder + demo + HR prompt)
**Files:** Create `examples/hiring_slice_demo.py`.
**Produces:** `HR_PARTS` (or a builder of `SystemPromptParts`); `SYNTHETIC_RESUMES` (3 `(CandidateRow, chunks)`), `ORG_RUBRIC`; `build_hiring_slice(*, embed_fn, embed_version, model) -> (agent, store, sid, manager)`; `run(question, *, embed_fn, embed_version, model) -> dict`; `main()`.

- [ ] **Step 1** — write the HR `SystemPromptParts`:
  - `org_policy`: "Jobpin Agent — an HR hiring assistant for an Australian employer."
  - `compliance`: recommend-only / HITL ("suggestions requiring human confirmation; never decide a hire/reject"); ground every claim in the provided candidate memory + cite the source; never fabricate qualifications; ignore protected attributes (age/gender/race/…) and proxies.
  - `role_permissions`: "Acting as a recruiter assistant; may summarise/compare/explain; may not message candidates or make decisions."
- [ ] **Step 2** — `build_hiring_slice`: build `CandidateMemoryProvider(SqliteVectorStore(), CandidateStructuredStore(), embed_fn, embed_model=…, embed_version=embed_version)` + `SemanticRAGProvider(SqliteVectorStore(), embed_fn, …, embed_version=embed_version)`; ingest `SYNTHETIC_RESUMES` (candidate) + `ORG_RUBRIC` (semantic); `CompositeMemoryProvider([semantic, candidate])`; `MemoryManager().add_provider(composite)`; `MemoryManagerHooks(manager)`; `SystemPromptParts(..HR.., provider_block=manager.build_system_prompt())`; `Agent(model, ToolRegistry(), SessionStore(":memory:"), hooks=hooks, parts=parts, tracer=Tracer())`; create session; return.
- [ ] **Step 3** — `run(question, ...)`: build, `agent.run_turn(sid, question)`, gather `sent = model.calls[0]` if fake (for the test) — actually return `{"answer", "recall_in_prompt": <KEY in the composed prompt>, "has_citation", "fenced", "steps"}`. For the real model, `model.calls` doesn't exist; guard: only inspect `model.calls` when present (fake). Compute recall flags from the session's composed messages instead — simplest: re-derive from `hooks.prefetch(question, sid)` (the inner block) to confirm a candidate + citation were recalled, independent of model type.
- [ ] **Step 4** — `main()`: `config = CoreConfig.from_env()`; if key → `embed_fn = openai_embedder(api_key=config.openai_api_key)`, `embed_version = "openai:text-embedding-3-small"`, `model = OpenAIProvider(config)`, print "(real OpenAI)"; else → `embed_fn = hashing_embedder(256)`, `embed_version = "hash@256"`, `model = FakeProvider([ModelResponse(text="<offline: set OPENAI_API_KEY to see a real shortlist>")])`, print "(offline/fake — no key)". Run the default hiring question; print the answer + recalled citations + steps. UTF-8 stdout.
- [ ] **Step 5 — commit** `feat(slice): hiring vertical-slice builder + demo + HR system prompt`.

Synthetic résumés (clearly fake; distinctive content lives in the PROSE, not the columns — so recall must come from the vector store):
- `cand_ada` — skills `["go","kafka"]`; chunk: "Architected a globally-distributed, eventually-consistent payments ledger at 2M tx/s; led a monolith→event-driven microservices migration; mentored four engineers."
- `cand_grace` — skills `["python","postgres"]`; chunk: "Built and operated the data platform; tuned Postgres for OLTP at scale; on-call lead; strong incident reviews."
- `cand_bo` — skills `["salesforce"]`; chunk: "Enterprise SaaS sales lead; consistent quota over-achievement in fintech."
`ORG_RUBRIC` (semantic, `memory_key="acme:apac:semantic:rubric"`): "Score SWE candidates on demonstrated impact and operational maturity, not tenure; backend roles weight distributed-systems and reliability experience."
Default question: "We're hiring a senior backend engineer for a high-throughput payments platform. Who in our pool fits, and why? Cite the evidence; flag this as a suggestion for human review."

### Task 3: tests (deterministic wiring + opt-in real)
**Files:** `agent/tests/test_hiring_slice.py`.
- [ ] **Deterministic wiring** (`hashing_embedder(256)` + `FakeProvider`): query uses words present in `cand_ada`'s prose ("globally-distributed payments ledger mentored engineers"); `run(...)` → assert `recall_in_prompt` (`cand_ada` key in the recall) and `has_citation` (`source:` present) and `fenced`. Build a turn through a real §1.1 `Agent` (FakeProvider, scripted text) and assert the composed prompt the model saw contains the HR/HITL framing **and** the recalled candidate + citation (`model.calls[0]`).
- [ ] **`openai_embedder` lazy** — constructs without a key/network (callable); with an injected fake client returns the fake vector.
- [ ] **Opt-in real** — `@pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"))`: build with `openai_embedder` + `OpenAIProvider(CoreConfig.from_env())`, run the hiring question, assert the answer is non-empty and mentions a candidate name. (Author does NOT run this.)
- [ ] Run the deterministic ones → pass; commit `test(slice): deterministic hiring-slice wiring + opt-in real-OpenAI test`.

### Task 4: docs
- [ ] Plan §1.15 pull-forward note (EN+中文): a thin recall+explain slice with a real model was built early; the full slice (parsing, governance gate, P95) remains §1.15.
- [ ] Bilingual devlog `site/devlog/p0-vertical-slice-hiring{,-EN}.md` to the §6 standard; devlog index; `CLAUDE.md` §8 status.
- [ ] Full `python -m pytest` green; commit `docs(slice): plan §1.15 pull-forward note + bilingual devlog + status`.

## Post-implementation (per `CLAUDE.md` §5)
- [ ] Full offline pytest green (note count). Triple-review; fix Plan-first if needed; apply fixes.
- [ ] Offer to push (kept gate); do NOT run the real-OpenAI test unsolicited.

## Self-Review
1. **Coverage:** embedder→T1, slice/demo/HR-prompt→T2, tests→T3, docs→T4. ✓
2. **Placeholders:** code/instructions concrete; the real-test is explicitly skip-guarded. ✓
3. **Types:** `openai_embedder`, `build_hiring_slice`, `run`, `SystemPromptParts`, the §1.4/§1.3/§1.1 APIs used consistently. ✓
4. **No core change / no unsolicited spend:** T2/T3 attach via hooks+parts only; the real path is opt-in and not author-run. ✓
