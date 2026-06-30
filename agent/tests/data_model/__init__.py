"""Tests for the §1.8 canonical data model + local audit log.

EN — Deterministic, offline tests for the canonical entities, the roll-forward/back migrations, the
canonical append-only audit (incl. the read-path actions + reconciliation import of the §1.5/§1.7
forerunners), and the CanonicalStore CRUD. 中文 — 对规范实体、前滚/后滚迁移、规范仅追加审计（含读路径动作 +
§1.5/§1.7 先行者对账导入）与 CanonicalStore CRUD 的确定性离线测试。
"""
