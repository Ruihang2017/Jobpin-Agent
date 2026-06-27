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
