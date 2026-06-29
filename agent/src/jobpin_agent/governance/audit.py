"""Append-only local audit log — who / what / when / why (§1.5).

EN —
A local, append-only record of every governed memory action, supporting NDB forensics and ADM
transparency (Production Plan §1.0 / §1.5). Each row carries the §1.0 shared fields: actor (who),
action (what — ``read`` / ``write:add`` / ``write:replace`` / ``write:remove`` / ``erase`` / ``recall``),
target_key (the memory_key), a dual timestamp (monotonic + wall clock), reason (why), and result
(``ok`` / ``rejected:<code>``). It is intentionally append-only: the class exposes no update or delete
method. This is the minimal forerunner of the §1.8 canonical ``AuditRecord`` relational table.

中文 —
对每个受治理记忆动作的本地仅追加记录，支撑 NDB 取证与 ADM 透明（生产计划 §1.0 / §1.5）。每行携带 §1.0 共享字段：
actor（谁）、action（做什么——``read`` / ``write:add`` / ``write:replace`` / ``write:remove`` / ``erase`` /
``recall``）、target_key（memory_key）、双时间戳（单调 + 墙钟）、reason（为何）、result（``ok`` / ``rejected:<code>``）。
刻意仅追加：本类不提供更新或删除方法。这是 §1.8 规范 ``AuditRecord`` 关系表的最小先行者。
"""
from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


@dataclass
class AuditRecord:
    """One audit-log row (the §1.0 who/what/when/why fields).

    EN —
    Attributes: actor; action; target_key; at_monotonic (a ``time.monotonic()`` reading for ordering);
    at_wall (ISO-8601 UTC wall clock); reason; result.
    中文 —
    属性：actor；action；target_key；at_monotonic（用于排序的 ``time.monotonic()`` 读数）；at_wall（ISO-8601 UTC
    墙钟）；reason；result。
    """

    actor: str
    action: str
    target_key: str
    at_monotonic: float
    at_wall: str
    reason: str
    result: str


class AuditLog:
    """An append-only SQLite audit log.

    EN —
    Construct over ``:memory:`` (tests) or a file path (real). ``record`` appends a row stamping both a
    monotonic and a wall-clock time; ``query`` reads rows back (optionally filtered). There is no
    mutation API — append-only by construction.

    中文 —
    在 ``:memory:``（测试）或文件路径（真实）上构造。``record`` 追加一行并同时打上单调与墙钟时间；``query`` 读回行
    （可选过滤）。无修改 API——按构造即仅追加。
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        """Open (or create) the audit log and ensure its schema.

        EN: Args: db_path (``:memory:`` for ephemeral). 中文：参数：db_path（``:memory:`` 为临时）。
        """
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS audit_log ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, actor TEXT, action TEXT, target_key TEXT, "
            "at_monotonic REAL, at_wall TEXT, reason TEXT, result TEXT)"
        )
        self._conn.commit()

    def record(self, actor: str, action: str, target_key: str, *, reason: str = "", result: str = "ok") -> None:
        """Append one audit row (stamps the dual timestamp).

        EN: Args: actor; action; target_key; reason; result. Returns: None.
        中文：参数：actor；action；target_key；reason；result。返回：None。
        """
        self._conn.execute(
            "INSERT INTO audit_log (actor, action, target_key, at_monotonic, at_wall, reason, result) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (actor, action, target_key, time.monotonic(),
             datetime.now(timezone.utc).isoformat(), reason, result),
        )
        self._conn.commit()

    def query(self, *, target_key: Optional[str] = None, action: Optional[str] = None) -> List[AuditRecord]:
        """Read audit rows in insertion order, optionally filtered by target_key / action.

        EN: Args: target_key; action. Returns: matching ``AuditRecord``s, oldest first.
        中文：参数：target_key；action。返回：匹配的 ``AuditRecord``，最早在前。
        """
        sql = "SELECT actor, action, target_key, at_monotonic, at_wall, reason, result FROM audit_log"
        clauses: List[str] = []
        params: List[str] = []
        if target_key is not None:
            clauses.append("target_key = ?")
            params.append(target_key)
        if action is not None:
            clauses.append("action = ?")
            params.append(action)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY id"
        return [AuditRecord(*row) for row in self._conn.execute(sql, params).fetchall()]
