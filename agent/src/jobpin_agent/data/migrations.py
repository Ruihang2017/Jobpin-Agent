"""In-house versioned schema migrations (§1.8) — roll forward and back, no Alembic.

EN —
A minimal stdlib migration runner over SQLite (the Plan's exit criterion: migrations that roll forward
AND back). A ``schema_version`` table tracks the applied version; ``MIGRATIONS`` is an ordered list of
``(version, up, down)`` SQL scripts. v1 lands the full M1–M3 subset + ``audit_log`` (future entities add
v2, v3, …). No third-party dependency.

中文 —
SQLite 上的最小标准库迁移运行器（计划退出标准：迁移可前滚与后滚）。``schema_version`` 表跟踪已应用版本；
``MIGRATIONS`` 是 ``(version, up, down)`` SQL 脚本的有序列表。v1 落地完整 M1–M3 子集 + ``audit_log``（未来实体加 v2、v3…）。
无第三方依赖。
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from .schema import TABLES


@dataclass
class Migration:
    """One schema migration step.

    EN: Attributes: version (int, ascending); up (SQL to apply); down (SQL to revert).
    中文：属性：version（整数，升序）；up（应用 SQL）；down（回退 SQL）。
    """

    version: int
    up: str
    down: str


# v1: the full M1–M3 subset + audit_log in one migration. Future entities/columns land as v2, v3, ….
# NOTE: the down-migration DROPs audit_log too — a full rollback to 0 destroys the append-only forensic
# history. That is acceptable for dev/test schema management; a production rollback must back up audit_log
# first (it is the tamper-evident record). v2+ migrations should be wrapped per-migration for atomicity.
_V1_UP = ";\n".join(TABLES.values())
_V1_DOWN = ";\n".join(f"DROP TABLE IF EXISTS {name}" for name in TABLES)
MIGRATIONS = [Migration(1, _V1_UP, _V1_DOWN)]
LATEST = max(m.version for m in MIGRATIONS)


def current_version(conn: sqlite3.Connection) -> int:
    """Return the applied schema version (0 if never migrated).

    EN: Args: conn. Returns: the integer version. (Ensures the ``schema_version`` table exists.)
    中文：参数：conn。返回：整数版本。（确保 ``schema_version`` 表存在。）
    """
    conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER)")
    row = conn.execute("SELECT version FROM schema_version").fetchone()
    return row[0] if row else 0


def _set_version(conn: sqlite3.Connection, version: int) -> None:
    """Persist the current schema version (single-row table).

    EN: Args: conn; version. 中文：参数：conn；version。
    """
    conn.execute("DELETE FROM schema_version")
    conn.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))


def migrate(conn: sqlite3.Connection, to_version: int = LATEST) -> None:
    """Migrate the connection forward or backward to ``to_version`` (roll-forward/back).

    EN —
    Args: conn; to_version (default ``LATEST``; ``0`` reverts everything). Applies each migration's ``up``
    in ascending order when moving forward, or each ``down`` in descending order when moving back, then
    records the new version. Returns: None.

    中文 —
    参数：conn；to_version（默认 ``LATEST``；``0`` 全部回退）。前进时按升序应用各迁移 ``up``，后退时按降序应用各 ``down``，
    随后记录新版本。返回：None。
    """
    version = current_version(conn)
    if to_version > version:
        for m in sorted(MIGRATIONS, key=lambda m: m.version):
            if version < m.version <= to_version:
                conn.executescript(m.up)
                version = m.version
    elif to_version < version:
        for m in sorted(MIGRATIONS, key=lambda m: m.version, reverse=True):
            if to_version < m.version <= version:
                conn.executescript(m.down)
                version = m.version - 1
    # Record the version ACTUALLY reached, not the requested target (triple-review fix: a target that
    # overshoots LATEST or undershoots 0 must not be recorded as if applied).
    _set_version(conn, version)
    conn.commit()


__all__ = ["Migration", "MIGRATIONS", "LATEST", "current_version", "migrate"]
