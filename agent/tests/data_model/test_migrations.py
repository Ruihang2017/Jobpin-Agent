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
    assert {"candidate", "audit_log", "memory_record", "consent"} <= _tables(conn)
    migrate(conn, 0)
    assert current_version(conn) == 0
    assert "candidate" not in _tables(conn)
    migrate(conn, LATEST)
    assert "candidate" in _tables(conn)
