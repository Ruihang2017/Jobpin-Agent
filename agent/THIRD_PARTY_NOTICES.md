# Third-Party Notices

## Hermes Agent (Nous Research) — MIT License

Portions of this product are **ported and adapted** from the Hermes Agent
(https://github.com/NousResearch/hermes-agent), used here under the MIT License.
The upstream source is vendored read-only as a git submodule at
`../reference/hermes/`.

Files derived from Hermes will be listed here as they are ported, e.g.:

- `src/jobpin_agent/memory/...`   ⟵ derived from `tools/memory_tool.py`
- `src/jobpin_agent/memory/...`   ⟵ derived from `agent/memory_provider.py`, `agent/memory_manager.py`
- `src/jobpin_agent/security/...` ⟵ derived from `threat_patterns.py`

(No files are ported yet. Keep the MIT copyright + license text below in any
substantial copied portion.)

## §1.1 Agent Core — provenance (design-derived; no substantial code copied)

| Jobpin file | Hermes source (design borrowed) | Strategy |
|---|---|---|
| `core/agent_loop.py` | `agent/conversation_loop.py::run_conversation` | New (rewrite, borrows turn-loop concept) |
| `core/system_prompt.py` | `agent/system_prompt.py::build_system_prompt` / `format_tools_for_system_message` | New (rewrite, borrows fixed-order assembly) |
| `core/delegation.py` | `on_delegation` pattern | New (borrows skip_memory + parent-observes invariant) |
| `core/hooks.py` | `agent/memory_provider.py` lifecycle (prefetch/sync/on_pre_compress/on_session_switch) | New (interface seam only) |
| `core/session_store.py` | Hermes SQLite session persistence | New (rewrite) |
| `core/model/*` | Hermes provider-agnostic model layer | New (minimal ABC + OpenAI adapter) |

No substantial Hermes code is copied at §1.1 (rewrite). Code-porting of the memory subsystem
(`memory_tool.py` / `memory_provider.py` / `memory_manager.py`, `threat_patterns.py`) begins at §1.2,
at which point the MIT copyright + licence text below applies to the copied portions.

## §1.2 Memory port — provenance (PORTED CODE — MIT, see notice below)

| Jobpin file | Hermes source | Strategy |
|---|---|---|
| `src/jobpin_agent/memory/store.py` | `tools/memory_tool.py::MemoryStore` (+ `ENTRY_DELIMITER`, `_drift_error`, helpers) | **Port** (algorithms verbatim) |

Adaptations: targets renamed `memory→org` / `user→recruiter` (files `ORG.md` / `RECRUITER.md`); the
injection scan is injected (`scan_entry`; the real `threat_patterns` is ported at §1.6); char budgets
recalibrated; the governance header is deferred to §1.5. The core algorithms — dedup, fixed-length
budget, atomic temp→fsync→`os.replace` write under a `.lock`, drift detection, `apply_batch`
all-or-nothing, the lean success response — are unchanged. The MIT copyright + licence text below is
retained for these copied portions.

## §1.3 Memory port ② — provenance (PORTED CODE — MIT, see notice below)

| Jobpin file | Hermes source | Strategy |
|---|---|---|
| `src/jobpin_agent/memory/provider.py` | `agent/memory_provider.py::MemoryProvider` | **Port** (full contract) |
| `src/jobpin_agent/memory/manager.py` | `agent/memory_manager.py::{MemoryManager, normalize_tool_schema, _SYNC_DRAIN_TIMEOUT_S}` | **Port** (method-by-method) |
| `src/jobpin_agent/memory/fence.py` | `agent/memory_manager.py::{sanitize_context, build_memory_context_block, _FENCE_*}` | **Port** (+ `build_memory_context_inner` adaptation) |

Adaptations (the §1.3 trims): `_strip_skill_scaffolding` is a pass-through (no /skill layer); local
`tool_error` (was `tools.registry.tool_error`); local `_CORE_TOOL_NAMES` (was `toolsets._HERMES_CORE_TOOLS`);
`initialize_all` injects no `hermes_home`; `build_memory_context_inner` is added so the §1.1 loop owns the
outer `<memory-context>` tags. NOT ported here (deferred): `StreamingContextScrubber` (→§1.6),
`inject_memory_provider_tools` / `memory_provider_tools_enabled` (→§1.5). The single-worker serial
executor, `flush_pending` barrier, bounded drain, failure-isolation try/except, single-external rule,
shadow guard, schema normalisation, and the fence regexes are unchanged. The `BuiltinMemoryProvider`
(`memory/providers/builtin.py`) is new code implementing the ported ABC over the §1.2 store. The MIT
copyright + licence text below is retained for these copied portions.

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
