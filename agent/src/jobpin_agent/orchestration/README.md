# `orchestration/` — Layer B long-running orchestration (§1.7)

## English
The state-machine layer Hermes lacks (PRD §2.6/§13.1). Layer A (`core/` + `memory/`) is single-shot
agent inference + memory; **Layer B** is the cross-day, multi-party, **resumable** business process — the
hiring loop. This package is a lightweight, **in-house** state machine satisfying three hard persistence
contracts: **crash recovery**, **cross-day pause/resume**, and **external side-effect idempotency**. It is
the **skeleton** only — the real recruitment-process states are Phase 1 M3, and the upgrade to
Temporal/LangGraph is reserved for if the skeleton fails the contract (§1.12 spike). Net-new (no Hermes
port). Persisted to local SQLite, consistent with `core/session_store.py`.

- `state_machine.py` — `Status` (running/suspended/awaiting_hitl/done/failed), `ProcessInstance` +
  `Transition` dataclasses, **`ProcessDefinition`** (declared states + legal transitions + hitl/suspend/
  terminal classes), and **`ProcessEngine`** (`start` / `transition` / `await_hitl` / `resume_hitl` /
  `suspend` / `resume` / `fail`) — every transition is **validated** against the definition, persisted,
  and appended to the auditable history. Illegal transitions raise `IllegalTransition`.
- `store.py` — **`OrchestrationStore`** (SQLite): `process_instances` (upserted), `transitions`
  (append-only, the audit basis), `idempotency`. The recovery load anchor; a fresh store over the same
  file sees committed data (how a restart recovers).
- `idempotency.py` — **`IdempotencyStore.run_once(key, effect_fn)`**: register-before-execute dedup —
  binds each external side effect to a deterministic key; a present key on replay skips (never re-sends).
- `recovery.py` — **`recover(store)`**: the crash-recovery loader (returns the non-terminal instances to
  resume).

## 中文
Hermes 缺失的状态机层（PRD §2.6/§13.1）。Layer A（`core/` + `memory/`）是单次 agent 推理 + 记忆；**Layer B** 是
跨天、多方、**可恢复**的业务流程——招聘 loop。本包是轻量、**自建**的状态机，满足三条硬持久化契约：**崩溃恢复**、
**跨天暂停/恢复**、**外部副作用幂等**。它仅为**骨架**——真实招聘流程状态在第一阶段 M3，升级到 Temporal/LangGraph 保留至
骨架未达契约时（§1.12 spike）。新增（非 Hermes 移植）。持久化到本地 SQLite，与 `core/session_store.py` 一致。

- `state_machine.py` — `Status`（running/suspended/awaiting_hitl/done/failed）、`ProcessInstance` +
  `Transition` 数据类、**`ProcessDefinition`**（声明的状态 + 合法转移 + hitl/挂起/终止分类）与 **`ProcessEngine`**
  （`start` / `transition` / `await_hitl` / `resume_hitl` / `suspend` / `resume` / `fail`）——每次转移都对定义**校验**、
  持久化并追加到可审计历史。非法转移抛 `IllegalTransition`。
- `store.py` — **`OrchestrationStore`**（SQLite）：`process_instances`（upsert）、`transitions`（仅追加，审计基础）、
  `idempotency`。恢复加载锚点；在同一文件上新建存储即可见已提交数据（重启据此恢复）。
- `idempotency.py` — **`IdempotencyStore.run_once(key, effect_fn)`**：执行前登记去重——把每个外部副作用绑定到确定性键；
  重放时键已存在则跳过（绝不重发）。
- `recovery.py` — **`recover(store)`**：崩溃恢复加载器（返回待恢复的非终止实例）。
