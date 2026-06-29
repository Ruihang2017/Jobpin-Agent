"""Append-only local audit log — who / what / when / why (§1.5).

EN —
A local, append-only record of every governed memory action, supporting NDB forensics and ADM
transparency (Production Plan §1.0 / §1.5). Each row carries the §1.0 shared fields: actor (who),
action (what), target_key (the memory_key), a dual timestamp (monotonic + wall clock), reason (why),
and result (``ok`` / ``rejected:<code>``). It is intentionally append-only: the class exposes no update
or delete method. This is the minimal forerunner of the §1.8 canonical ``AuditRecord`` relational table.

SCOPE (§1.5): the WRITE path emits ``write:add`` / ``write:replace`` / ``write:remove`` / ``write:ingest``
(``ok`` or ``rejected:<code>``) and the ERASURE path emits ``erase``. The READ path (``recall`` /
``rejected:rbac``) is the §1.0 vocabulary but is **deferred to §1.8**: recall runs on the §1.3 background
``mem-sync`` worker, and read-path forensics belong with the thread-safe canonical ``AuditRecord`` table
(§1.8). RBAC already enforces the recall *filter* in §1.5; what is deferred is the read *trail*. The
connection is opened ``check_same_thread=False`` with a lock so §1.8 can record from the worker.

中文 —
对每个受治理记忆动作的本地仅追加记录，支撑 NDB 取证与 ADM 透明（生产计划 §1.0 / §1.5）。每行携带 §1.0 共享字段：
actor（谁）、action（做什么）、target_key（memory_key）、双时间戳（单调 + 墙钟）、reason（为何）、result
（``ok`` / ``rejected:<code>``）。刻意仅追加：本类不提供更新或删除方法。这是 §1.8 规范 ``AuditRecord`` 关系表的最小先行者。

范围（§1.5）：写路径发出 ``write:add`` / ``write:replace`` / ``write:remove`` / ``write:ingest``（``ok`` 或
``rejected:<code>``），擦除路径发出 ``erase``。读路径（``recall`` / ``rejected:rbac``）属 §1.0 词汇但**推迟到 §1.8**：
召回运行于 §1.3 后台 ``mem-sync`` 工作线程，读路径取证应与线程安全的规范 ``AuditRecord`` 表（§1.8）同处。RBAC 在 §1.5
已强制召回*过滤*；推迟的是读*痕迹*。连接以 ``check_same_thread=False`` + 锁打开，使 §1.8 可从工作线程记录。
"""
from __future__ import annotations

import sqlite3
import threading
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
        # check_same_thread=False + a lock: §1.5 writes from the main/tool thread, but §1.8's read-path
        # audit will record from the §1.3 background mem-sync worker — make that safe now.
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock:
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS audit_log ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, actor TEXT, action TEXT, target_key TEXT, "
                "at_monotonic REAL, at_wall TEXT, reason TEXT, result TEXT)"
            )
            self._conn.commit()

    def record(self, actor: str, action: str, target_key: str, *, reason: str = "", result: str = "ok") -> None:
        """Append one audit row (stamps the dual timestamp). Thread-safe.

        EN: Args: actor; action; target_key; reason; result. Returns: None.
        中文：参数：actor；action；target_key；reason；result。返回：None。
        """
        with self._lock:
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
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [AuditRecord(*row) for row in rows]
