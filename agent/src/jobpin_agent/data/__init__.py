"""Canonical data model + local audit log (§1.8).

EN —
The relational backbone of the HR lifecycle. This package lands the **canonical entities** (the M1–M3
subset: Candidate / Job / Application / Interview / Consent / Org / User) plus the two **seam tables** —
``AuditRecord`` and ``MemoryRecord`` — that map the §1.0 shared vocabulary, the §1.4 vector/structured
records, and the §1.5 governance schema onto one relational layer, so every compliance/forensics query
(APP 12/13 access & correction, the bias audit, NDB) starts from here. It carries `tenant_id` as a
single-tenant placeholder (no multi-tenant infra) and uses an append-only audit log (no event sourcing) —
both deferred per PRD §13.1. The §1.5 governance ``AuditLog`` and the §1.7 transition log remain as
forerunners and are reconciled into the canonical audit by **import** (non-invasive — no rewire). Net-new
(no Hermes port); standalone (no ``core``/``agent_loop`` change).

中文 —
HR 生命周期的关系骨架。本包落地**规范实体**（M1–M3 子集：Candidate / Job / Application / Interview / Consent / Org /
User）外加两张**接缝表**——``AuditRecord`` 与 ``MemoryRecord``——把 §1.0 共享词汇、§1.4 向量/结构化记录与 §1.5 治理模式
映射到一个关系层，使每个合规/取证查询（APP 12/13 访问与更正、偏见审计、NDB）皆从此开始。它以 `tenant_id` 作单租户占位
（无多租户基础设施）、用仅追加审计日志（无事件溯源）——二者按 PRD §13.1 推迟。§1.5 治理 ``AuditLog`` 与 §1.7 转移日志
作为先行者保留，并以**导入**方式（非侵入——不重写）对账进规范审计。新增（非 Hermes 移植）；独立（不改 ``core``/``agent_loop``）。
"""
