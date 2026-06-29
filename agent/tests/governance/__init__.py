"""Tests for the §1.5 HR memory governance package.

EN — Deterministic unit + integration tests for the governance shell (namespace, labels, audit, bias
hygiene, RBAC, retention, write-gate, governed tool, erasure) and the end-to-end composition (no loop
change). All stores use ``:memory:`` SQLite; no network, no cost.

中文 — §1.5 治理外壳（命名空间、标签、审计、偏见卫生、RBAC、留存、写门控、受治理工具、擦除）的确定性单元 + 集成
测试，以及端到端组合（不改循环）。所有存储用 ``:memory:`` SQLite；无网络、无费用。
"""
