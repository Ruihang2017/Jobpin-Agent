"""Tests for the §1.7 Layer B orchestration skeleton.

EN — Deterministic, offline tests for the store, the declarative state-machine engine, idempotency, the
recovery loader, and the three persistence contracts (crash recovery / cross-day pause-resume / external
side-effect idempotency). Durability tests use a file ``db_path`` (a fresh store over the same file).
中文 — 对存储、声明式状态机引擎、幂等、恢复加载器与三条持久化契约（崩溃恢复 / 跨天暂停-恢复 / 外部副作用幂等）的
确定性离线测试。持久化测试用文件 ``db_path``（在同一文件上新建存储）。
"""
