# `memory/` — Memory Subsystem

## English
The Memory Subsystem (Production Plan §1.2–1.6). This point (§1.2) ships the
curated, file-backed layer; later points add orchestration, vectors, governance,
and injection defence.

- `store.py` — **`MemoryStore`**, ported from Hermes `tools/memory_tool.py` (MIT).
  A bounded, file-persisted curated store with two targets — **`org`** (`ORG.md`:
  hiring standards / rubrics / policy) and **`recruiter`** (`RECRUITER.md`:
  preferences / the hiring "bar"). Two parallel states per target: a **frozen
  snapshot** (enters the system prompt, stable per session) and a **live entry
  list** (atomic writes, `.lock`, drift detection, `apply_batch` all-or-nothing).
  Injection scanning is an **injected `scan_entry`** callable (default pass-through;
  the real `threat_patterns` lands at §1.6).

Deferred: wiring into the agent loop = §1.3 (`MemoryProvider`/`MemoryManager`);
the governance header (provenance/consent/retention) = §1.5; real threat patterns
= §1.6; the embedded vector store + entity providers = §1.4.

## 中文
记忆子系统（生产计划 §1.2–1.6）。本节点（§1.2）交付经策展的文件型层；后续节点加入编排、向量、治理与注入防御。

- `store.py` — **`MemoryStore`**，移植自 Hermes `tools/memory_tool.py`（MIT）。一个有界、文件持久化的策展存储，
  含两个目标——**`org`**（`ORG.md`：招聘标准 / 评分细则 / 政策）与 **`recruiter`**（`RECRUITER.md`：偏好 /
  招聘“标尺”）。每个目标两个并行状态：**冻结快照**（进入系统提示，每会话稳定）与**实时条目列表**（原子写、`.lock`、
  漂移检测、`apply_batch` 全有或全无）。注入扫描为**注入式 `scan_entry`** 可调用对象（默认放行；真实
  `threat_patterns` 在 §1.6 落地）。

推迟：接入 agent 循环 = §1.3（`MemoryProvider`/`MemoryManager`）；治理头（来源/同意/留存）= §1.5；真实威胁模式
= §1.6；嵌入式向量库 + 实体 provider = §1.4。
