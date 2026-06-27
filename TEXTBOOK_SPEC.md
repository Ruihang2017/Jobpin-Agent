# TEXTBOOK_SPEC.md — Engineering Quality Yardstick

The quality bar for this repository, referenced throughout the Production Plan
(`site/plan/02-Production-Plan*.md`). It exists so that any deliverable can be **verified by a
reviewer who opens the exact test / file / command** — not taken on trust. It applies especially to
Phase 0 (the Hermes port) and to every phase gate thereafter.

> One line: **name the real thing, and prove it with something runnable.**

## Tenet 1 — When porting a Hermes mechanism, ground it in the real source

Wherever work "ports a Hermes mechanism", it must:
- **Name the real upstream file and symbol** — e.g. `MemoryStore` in `tools/memory_tool.py`,
  `MemoryProvider` in `agent/memory_provider.py`, `MemoryManager` in `agent/memory_manager.py`,
  threat patterns in `tools/threat_patterns.py`. The pinned source is at `reference/hermes/`.
- **Explain what changed after the port and why** (local-first, HR governance, trimmed for clean
  ownership, relaxed "single external Provider", etc.).
- **Record the derivation** in `agent/THIRD_PARTY_NOTICES.md`, keeping the MIT copyright + licence
  text in any substantial copied portion (PRD §2.7).
- Carry its **own security review** — MIT is "as is"; a regulated product must not blindly trust
  upstream. Verify transitive-dependency licences too.

Vague claims like "ported the memory system" without the file/symbol and the diff are **not
acceptable**.

## Tenet 2 — Every deliverable has a testable acceptance measure

- **A deliverable with no acceptance measure is not a deliverable.** Each one states "How to verify
  this yourself": the exact test, file, or command, and the expected result.
- Every **threshold** is a **measurable quantity** — e.g. "recall P95 < 800 ms at SMB scale on
  the published minimum hardware tier", not "fast". State the scale, hardware, and method.
- Prefer automated checks (pytest, eval harness, conformance tests) over prose assertions. CI gates
  (quality + fairness smoke) enforce the bar where possible.

## Tenet 3 — Verification stance ("How to verify this yourself")

A phase/workstream passes when a reviewer can open the listed tests/files/commands and confirm each
item independently. Acceptance lines in the Production Plan are the source of truth; command forms
shown there are placeholders — the actual CI task names in this repo take precedence.

## How this is used

- **Authoring** specs/plans: every task ends in an independently testable deliverable with its check.
- **Reviewing**: reject deliverables that lack a real source grounding (Tenet 1) or a runnable
  acceptance measure (Tenet 2).
- **Porting** (Phase 0): see `agent/CLAUDE.md` for the porting workflow that implements Tenet 1.
