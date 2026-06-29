# `site/devlog/` — build journal (study reference)

## English
A bilingual write-up per implemented Production-Plan point: **how** it was built
and **why** (including review findings). The repo is meant to double as a study
reference, so these explain decisions, not just code. Naming:
`p<phase>-<point>-<slug>-EN.md` (English) + `p<phase>-<point>-<slug>.md` (中文).

- `p0-1.1-agent-core-EN.md` / `p0-1.1-agent-core.md` — Phase 0 §1.1 Agent Core.
- `p0-1.2-memory-store-EN.md` / `p0-1.2-memory-store.md` — Phase 0 §1.2 file-backed MemoryStore.
- `p0-1.3-memory-provider-manager-EN.md` / `p0-1.3-memory-provider-manager.md` — Phase 0 §1.3 MemoryProvider + MemoryManager (the memory seam).
- `p0-1.4-vector-entity-providers-EN.md` / `p0-1.4-vector-entity-providers.md` — Phase 0 §1.4 embedded vector store + Candidate/Semantic providers (+ minimal Composite).
- `p0-1.5-hr-memory-governance-EN.md` / `p0-1.5-hr-memory-governance.md` — Phase 0 §1.5 HR memory governance (write-gate + governed memory tool, RBAC, erasure, retention, bias hygiene, audit).
- `p0-1.6-injection-defence-EN.md` / `p0-1.6-injection-defence.md` — Phase 0 §1.6 injection-defence port (threat patterns + streaming scrubber + external-ingest door) + pre-compression fact-injection wiring.
- `p0-vertical-slice-hiring-EN.md` / `p0-vertical-slice-hiring.md` — Phase 0 thin hiring vertical slice with a real LLM (pulls §1.15 forward).

## 中文
每个已实现的生产计划节点一份双语记录：**如何**构建与**为何**（含评审发现）。本仓库意在兼作学习参考，故这些文档解释决策，
而不仅是代码。命名：`p<phase>-<point>-<slug>-EN.md`（英文）+ `p<phase>-<point>-<slug>.md`（中文）。

- `p0-1.1-agent-core-EN.md` / `p0-1.1-agent-core.md` — Phase 0 §1.1 Agent 内核。
- `p0-1.2-memory-store-EN.md` / `p0-1.2-memory-store.md` — Phase 0 §1.2 文件型 MemoryStore。
- `p0-1.3-memory-provider-manager-EN.md` / `p0-1.3-memory-provider-manager.md` — Phase 0 §1.3 MemoryProvider + MemoryManager（记忆接缝）。
- `p0-1.4-vector-entity-providers-EN.md` / `p0-1.4-vector-entity-providers.md` — Phase 0 §1.4 嵌入式向量库 + Candidate/Semantic provider（+ 最小 Composite）。
- `p0-1.5-hr-memory-governance-EN.md` / `p0-1.5-hr-memory-governance.md` — Phase 0 §1.5 HR 记忆治理（写门控 + 受治理记忆工具、RBAC、擦除、留存、偏见卫生、审计）。
- `p0-1.6-injection-defence-EN.md` / `p0-1.6-injection-defence.md` — Phase 0 §1.6 注入防御移植（威胁模式 + 流式清洗器 + 外部 ingest 入口）+ 压缩前事实注入接线。
- `p0-vertical-slice-hiring-EN.md` / `p0-vertical-slice-hiring.md` — Phase 0 真实 LLM 的薄招聘垂直切片（提前 §1.15）。
