"""Tests for ``data/migrations.py`` — roll forward to LATEST, roll back to 0, round-trip.

EN — the exit-criterion proof: migrations apply forward (tables exist) and revert (tables gone), and a
re-forward is clean. 中文 — 退出标准证明：迁移前滚（表存在）与后滚（表消失），再前滚干净。
"""
import sqlite3

from jobpin_agent.data.migrations import LATEST, current_version, migrate


def _tables(conn) -> set:
    """Return the set of user table names. EN/中文: table-name set."""
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def test_migrate_forward_then_back_round_trip():
    """migrate(LATEST) creates the schema; migrate(0) reverts it; re-forward restores it.

    EN: roll forward/back. 中文：前滚/后滚。
    """
    conn = sqlite3.connect(":memory:")
    assert current_version(conn) == 0
    migrate(conn, LATEST)
    assert current_version(conn) == LATEST
    subset = {"candidate", "job", "application", "interview", "consent", "org", "user", "memory_record", "audit_log"}
    assert subset <= _tables(conn)
    migrate(conn, 0)
    assert current_version(conn) == 0
    assert subset.isdisjoint(_tables(conn))          # ALL subset tables dropped on rollback
    migrate(conn, LATEST)
    assert current_version(conn) == LATEST and subset <= _tables(conn)


def test_migrate_records_achieved_version_not_overshoot():
    """An overshoot target records the version actually reached (LATEST), not the argument.

    EN: migrate(conn, 99) with LATEST==1 stamps LATEST. 中文：LATEST==1 时 migrate(conn, 99) 记录 LATEST。
    """
    conn = sqlite3.connect(":memory:")
    migrate(conn, 99)
    assert current_version(conn) == LATEST
