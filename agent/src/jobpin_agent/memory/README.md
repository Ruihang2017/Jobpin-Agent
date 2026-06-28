# `memory/` — Memory Subsystem

## English
The Memory Subsystem (Production Plan §1.2–1.6). §1.2 ships the curated, file-backed
store; §1.3 adds the provider interface + orchestrator + the seam that attaches it to
the §1.1 agent loop; later points add vectors (§1.4), governance (§1.5), and injection
defence (§1.6).

- `store.py` — **`MemoryStore`** (§1.2), ported from Hermes `tools/memory_tool.py` (MIT).
  A bounded, file-persisted curated store with two targets — **`org`** (`ORG.md`:
  hiring standards / rubrics / policy) and **`recruiter`** (`RECRUITER.md`:
  preferences / the hiring "bar"). Two parallel states per target: a **frozen
  snapshot** (enters the system prompt, stable per session) and a **live entry
  list** (atomic writes, `.lock`, drift detection, `apply_batch` all-or-nothing).
  Injection scanning is an **injected `scan_entry`** callable (default pass-through;
  the real `threat_patterns` lands at §1.6).
- `provider.py` — **`MemoryProvider`** ABC (§1.3), ported from `agent/memory_provider.py`.
  The uniform contract every memory backend implements (lifecycle + opt-in hooks).
- `manager.py` — **`MemoryManager`** (§1.3), ported from `agent/memory_manager.py`.
  Drives all providers: system-prompt assembly, `prefetch_all`, `sync_all` /
  `queue_prefetch_all` on a **single-worker serial background** executor, the
  `flush_pending` barrier, bounded drain on shutdown, failure isolation, the
  single-external-provider rule, the core-tool shadow guard, and tool routing.
- `fence.py` — the `<memory-context>` fence (§1.3): `sanitize_context` +
  `build_memory_context_block` + `build_memory_context_inner` (the §1.1 loop owns the
  outer tags, so the seam returns the inner block).
- `manager_hooks.py` — **`MemoryManagerHooks`** (§1.3): implements the §1.1
  `core/hooks.py::MemoryHooks` Protocol over a `MemoryManager` — the seam that attaches
  the backend with **no change to `agent_loop.py`**.
- `composition.py` — **`build_memory_backend(...)`** (§1.3): assembles store → builtin
  provider → manager → hooks and fills the §1.1 `memory_snapshot` / `provider_block` slots.
- `vector/` — **the embedded local vector store** (§1.4): `record.py` (`VectorRecord` schema),
  `store.py` (`VectorStore` ABC + stdlib `SqliteVectorStore` — brute-force cosine NN, `key_prefix`
  filter-before-NN, `delete_by_key_prefix` erasure cascade, single-`embed_version` drift guard),
  `reembed.py` (resumable re-embed migration). Real backend (sqlite-vec/LanceDB) swaps in post-§1.12.
- `structured.py` — **`CandidateStructuredStore`** (§1.4): a minimal SQLite store of candidate
  filter fields (skills/years/location/work_rights/consent) keyed by `memory_key`. Full canonical
  model = §1.8.
- `embedding.py` — **the embed seam** (§1.4): `EmbedFn` + a dependency-free `hashing_embedder`
  default + `cosine` + `embed_version`. Real BGE/OpenAI embedders inject behind `EmbedFn` (config).
- `benchmark.py` — **`run_recall_benchmark`** (§1.4): recall@k + P95 over labelled queries (§1.15/Phase 1).
- `providers/` — concrete providers. `builtin.py` = **`BuiltinMemoryProvider`** (§1.3); §1.4 adds
  `retrieval_base.py` (cached citation-bearing prefetch base), `semantic.py` =
  **`SemanticRAGProvider`** (KB retrieval), `candidate.py` = **`CandidateMemoryProvider`** (gated
  ingest, filter-before-NN, erasure cascade), and `composite.py` = minimal
  **`CompositeMemoryProvider`** (the sole external facade; broadcast prefetch/merge + unicast sync).

Deferred: the governed model-facing `memory` **write tool** + agent-surface tool
injection = §1.5; the **governance write gate** on entity ingest + **RBAC** `scope_filter` = §1.5;
the real vector backend = §1.12; the real embedder = config; real threat
patterns + `StreamingContextScrubber` + real pre-compression wiring = §1.6;
the **full** `CompositeMemoryProvider` (Employee, routing table, merge-consistency) = Phase 2 §3.2.

## 中文
记忆子系统（生产计划 §1.2–1.6）。§1.2 交付经策展的文件型存储；§1.3 加入 provider 接口 + 编排器 + 将其接入 §1.1
agent 循环的接缝；后续节点加入向量（§1.4）、治理（§1.5）与注入防御（§1.6）。

- `store.py` — **`MemoryStore`**（§1.2），移植自 Hermes `tools/memory_tool.py`（MIT）。一个有界、文件持久化的策展存储，
  含两个目标——**`org`**（`ORG.md`：招聘标准 / 评分细则 / 政策）与 **`recruiter`**（`RECRUITER.md`：偏好 /
  招聘“标尺”）。每个目标两个并行状态：**冻结快照**（进入系统提示，每会话稳定）与**实时条目列表**（原子写、`.lock`、
  漂移检测、`apply_batch` 全有或全无）。注入扫描为**注入式 `scan_entry`** 可调用对象（默认放行；真实
  `threat_patterns` 在 §1.6 落地）。
- `provider.py` — **`MemoryProvider`** ABC（§1.3），移植自 `agent/memory_provider.py`。每个记忆后端实现的统一契约
  （生命周期 + 可选钩子）。
- `manager.py` — **`MemoryManager`**（§1.3），移植自 `agent/memory_manager.py`。驱动所有 provider：系统提示装配、
  `prefetch_all`、在**单工作线程串行后台**执行器上的 `sync_all` / `queue_prefetch_all`、`flush_pending` 屏障、
  关闭时有界排空、失败隔离、单外部 provider 规则、核心工具影子守卫与工具路由。
- `fence.py` — `<memory-context>` 围栏（§1.3）：`sanitize_context` + `build_memory_context_block` +
  `build_memory_context_inner`（§1.1 循环拥有外层标签，故接缝返回内层块）。
- `manager_hooks.py` — **`MemoryManagerHooks`**（§1.3）：在 `MemoryManager` 之上实现 §1.1
  `core/hooks.py::MemoryHooks` 协议——**在不改动 `agent_loop.py`** 的前提下接入后端的接缝。
- `composition.py` — **`build_memory_backend(...)`**（§1.3）：装配 存储 → 内置 provider → manager → hooks，并填充
  §1.1 `memory_snapshot` / `provider_block` 槽位。
- `vector/` — **嵌入式本地向量库**（§1.4）：`record.py`（`VectorRecord` 模式）、`store.py`（`VectorStore` ABC +
  标准库 `SqliteVectorStore`——暴力余弦近邻、`key_prefix` 先过滤再近邻、`delete_by_key_prefix` 擦除级联、
  单 `embed_version` 漂移守卫）、`reembed.py`（可恢复重嵌入迁移）。生产后端（sqlite-vec/LanceDB）§1.12 后替换。
- `structured.py` — **`CandidateStructuredStore`**（§1.4）：最小 SQLite 候选人过滤字段库（技能/年限/地点/工作权利/同意），
  以 `memory_key` 为键。完整规范模型 = §1.8。
- `embedding.py` — **嵌入接缝**（§1.4）：`EmbedFn` + 无依赖 `hashing_embedder` 默认 + `cosine` + `embed_version`。
  真实 BGE/OpenAI 嵌入器经 `EmbedFn` 注入（配置）。
- `benchmark.py` — **`run_recall_benchmark`**（§1.4）：带标注查询的 recall@k + P95（§1.15/Phase 1）。
- `providers/` — 具体 provider。`builtin.py` = **`BuiltinMemoryProvider`**（§1.3）；§1.4 加入 `retrieval_base.py`
  （带引用的缓存 prefetch 基类）、`semantic.py` = **`SemanticRAGProvider`**（知识库检索）、`candidate.py` =
  **`CandidateMemoryProvider`**（受门控 ingest、先过滤再近邻、擦除级联）、`composite.py` = 最小
  **`CompositeMemoryProvider`**（唯一外部门面；广播 prefetch/归并 + 单播 sync）。

推迟：受治理的面向模型 `memory` **写工具** + agent 表面工具注入 = §1.5；实体 ingest 的**治理写门控** + **RBAC**
`scope_filter` = §1.5；真实向量后端 = §1.12；真实嵌入器 = 配置；真实威胁模式 + `StreamingContextScrubber` +
真实压缩前接线 = §1.6；**完整** `CompositeMemoryProvider`（Employee、路由表、归并一致性）= 第二阶段 §3.2。
