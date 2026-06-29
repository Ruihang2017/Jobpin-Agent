# `governance/` — HR Memory Governance (§1.5)

## English
The compliance shell around the memory subsystem (Production Plan §1.5; PRD §9.5) — **net-new** to the
project (Hermes lacks it). It wraps every memory write and recall in *namespace + provenance +
lawful-basis/consent labels + retention + RBAC + audit + bias hygiene*, moving the system from "can
remember" to "remembers compliantly, uses explainably, and can be erased". Governance is enforced in
the **governed write tool's write path** (the sole writer to the curated store, so the ported
`MemoryStore` stays unchanged) and on the **recall path** via the existing filter-before-NN `scope`
seam; erasure orchestrates the §1.4 `delete_by_key_prefix` cascade.

- `namespace.py` — **`MemoryKey`** + `parse`/`is_valid`/`prefix(level)` for `tenant:org:entity_type:entity_id`
  (Plan §1.0); single-tenant MVP placeholders `DEFAULT_TENANT`/`DEFAULT_ORG`; `ENTITY_TYPES`.
- `labels.py` — **`Provenance` / `ConsentLabel` / `RetentionPolicy`** dataclasses + `render_header` /
  `parse_header` (the §1.2 in-entry governance header); `CONSENT_REQUIRED_SOURCE_TYPES`, `LEGAL_BASES`.
- `audit.py` — **`AuditLog`** (append-only SQLite, who/what/when/why with a dual monotonic+wall
  timestamp) + **`AuditRecord`**. No mutation API. Minimal forerunner of §1.8's canonical table.
- `bias_hygiene.py` — **`scan`** + **`BiasFinding`**: protected-attribute (→ `rejected:bias`) and
  proxy-variable (→ `flagged:bias`) heuristic scanner. **Honest boundary**: a curated starter set, not a
  complete classifier; the Phase-1 bias audit owns the real model.
- `rbac.py` — **`Principal`** + **`scope_predicate`** (a `memory_key` prefix filter for recall least
  privilege, APP 11) + **`FULL_ACCESS`** default. Auth source deferred (PRD open-Q#8); §1.9 reuses this.
- `retention.py` — **`RETENTION_POLICIES`** (hired/not-hired/withdrawn, APP 11.2) + **`sweep`** (explicit
  TTL sweep, no background timer) + **`BackupAgeingRegister`** (the honest "backups age out" record).
- `write_gate.py` — **`GovernanceGate.validate`** + **`Decision`**: the first-class write pre-check —
  reject unlabelled/unconsented/biased writes with an audit code, else return the rendered header.
- `erasure.py` — **`Eraser.erase`**: the data-subject erasure pipeline (delete cascade → clear recall
  caches → audit `erase/ok` → register backup-ageing). APP 11.2 destruction; de-id of residue → §1.11.
- `tool_bridge.py` — **`build_memory_tool(manager)`**: a `core.tools.ToolSpec` bridging the
  `ToolRegistry` to `MemoryManager.handle_tool_call` (+ external mirror), so the governed `memory` write
  tool is model-callable with **no change to `agent_loop.py`**.

The governed `memory` write tool itself lives on `memory/providers/builtin.py::BuiltinMemoryProvider`
(opt-in via an injected `GovernanceGate`); this package supplies the gate, labels, audit, and bridge.

## 中文
记忆子系统的合规外壳（生产计划 §1.5；PRD §9.5）——本项目**新增**（Hermes 缺失）。它把每次记忆写入与召回包裹进
*命名空间 + 来源 + 合法依据/同意标签 + 留存 + RBAC + 审计 + 偏见卫生*，使系统从“能记住”升级为“合规地记住、可解释地
使用、可被擦除”。治理在**受治理写工具的写路径**上强制（策展存储的唯一写入者，故移植的 `MemoryStore` 保持不变），并
经既有“先过滤再近邻”的 `scope` 接缝作用于**召回路径**；擦除编排 §1.4 的 `delete_by_key_prefix` 级联。

- `namespace.py` — **`MemoryKey`** + `parse`/`is_valid`/`prefix(level)`，用于 `tenant:org:entity_type:entity_id`
  （计划 §1.0）；单租户 MVP 占位符 `DEFAULT_TENANT`/`DEFAULT_ORG`；`ENTITY_TYPES`。
- `labels.py` — **`Provenance` / `ConsentLabel` / `RetentionPolicy`** 数据类 + `render_header` /
  `parse_header`（§1.2 条目内治理头）；`CONSENT_REQUIRED_SOURCE_TYPES`、`LEGAL_BASES`。
- `audit.py` — **`AuditLog`**（仅追加 SQLite，谁/做什么/何时/为何，带单调+墙钟双时间戳）+ **`AuditRecord`**。
  无修改 API。§1.8 规范表的最小先行者。
- `bias_hygiene.py` — **`scan`** + **`BiasFinding`**：受保护属性（→ `rejected:bias`）与代理变量（→ `flagged:bias`）
  启发式扫描器。**诚实边界**：策展起步集，并非完整分类器；真正的模型由第一阶段偏见审计负责。
- `rbac.py` — **`Principal`** + **`scope_predicate`**（召回最小权限的 `memory_key` 前缀过滤，APP 11）+
  **`FULL_ACCESS`** 默认。鉴权来源推迟（PRD 开放问题 #8）；§1.9 复用此。
- `retention.py` — **`RETENTION_POLICIES`**（录用/未录用/撤回，APP 11.2）+ **`sweep`**（显式 TTL 扫描，无后台定时器）
  + **`BackupAgeingRegister`**（诚实的“备份老化”记录）。
- `write_gate.py` — **`GovernanceGate.validate`** + **`Decision`**：一等公民写预检——以审计码拒绝
  未标注/未同意/偏见写入，否则返回渲染好的头。
- `erasure.py` — **`Eraser.erase`**：数据主体擦除流水线（删除级联 → 清空召回缓存 → 审计 `erase/ok` → 登记备份老化）。
  APP 11.2 销毁；残留去标识化 → §1.11。
- `tool_bridge.py` — **`build_memory_tool(manager)`**：把 `ToolRegistry` 桥接到 `MemoryManager.handle_tool_call`
  （+ 外部镜像）的 `core.tools.ToolSpec`，使受治理的 `memory` 写工具可被模型调用且**不改动 `agent_loop.py`**。

受治理的 `memory` 写工具本体位于 `memory/providers/builtin.py::BuiltinMemoryProvider`（经注入 `GovernanceGate` 启用）；
本包提供门控、标签、审计与桥。
