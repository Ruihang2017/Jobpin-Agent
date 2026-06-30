# `data/` — Canonical data model + local audit log (§1.8)

## English
The relational backbone of the HR lifecycle (Plan §1.8). Lands the **canonical M1–M3 entities** + the two
**seam tables** (`AuditRecord` via `audit_log`, `MemoryRecord`) that map the §1.0 vocab, the §1.4 records,
and the §1.5 governance schema onto one relational layer. SQLite, `tenant_id` placeholder, append-only
audit (no event sourcing — PRD §13.1). Net-new (no Hermes port); standalone (no `core` change).

- `schema.py` — canonical entity dataclasses (`Candidate`, `Job`, `Application`, `Interview`, `Consent`,
  `Org`, `User`, `MemoryRecord`) + the `TABLES` DDL (incl. `audit_log`); `DEFAULT_TENANT`/`DEFAULT_ORG`.
- `migrations.py` — **`migrate(conn, to_version)`** + `MIGRATIONS`/`LATEST`/`current_version`: an in-house
  versioned runner that rolls **forward and back** (v1 = the full M1–M3 subset + `audit_log`).
- `store.py` — **`CanonicalStore`**: migrates on open, CRUD over the entities, and a shared `.audit`.
- `audit.py` — **`AuditStore`**: the canonical append-only audit (dual timestamp, read+write actions incl.
  the `recall`/`rejected:rbac` deferred from §1.5/§1.6) + `import_governance_audit` / `import_transitions`
  reconciliation of the §1.5/§1.7 forerunners (non-invasive — by import, no rewire).

Entity↔store routing is documented in `../../../../docs/entity-memory-mapping.md`. The §1.4
`CandidateStructuredStore` coexists as the retrieval projection (canonical store = source of truth).

## 中文
HR 生命周期的关系骨架（计划 §1.8）。落地**规范 M1–M3 实体** + 两张**接缝表**（`AuditRecord` 经 `audit_log`、
`MemoryRecord`），把 §1.0 词汇、§1.4 记录与 §1.5 治理模式映射到一个关系层。SQLite、`tenant_id` 占位、仅追加审计
（无事件溯源——PRD §13.1）。新增（非 Hermes 移植）；独立（不改 `core`）。

- `schema.py` — 规范实体数据类（`Candidate`、`Job`、`Application`、`Interview`、`Consent`、`Org`、`User`、
  `MemoryRecord`）+ `TABLES` DDL（含 `audit_log`）；`DEFAULT_TENANT`/`DEFAULT_ORG`。
- `migrations.py` — **`migrate(conn, to_version)`** + `MIGRATIONS`/`LATEST`/`current_version`：自建版本化运行器，
  可**前滚与后滚**（v1 = 完整 M1–M3 子集 + `audit_log`）。
- `store.py` — **`CanonicalStore`**：打开即迁移、对实体 CRUD，并共享 `.audit`。
- `audit.py` — **`AuditStore`**：规范仅追加审计（双时间戳、读+写动作含 §1.5/§1.6 推迟的 `recall`/`rejected:rbac`）
  + `import_governance_audit` / `import_transitions` 对账 §1.5/§1.7 先行者（非侵入——经导入，不重写）。

实体↔存储路由见 `../../../../docs/entity-memory-mapping.md`。§1.4 `CandidateStructuredStore` 作检索投影并存
（规范存储 = 事实来源）。
