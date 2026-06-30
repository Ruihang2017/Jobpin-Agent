"""Canonical append-only audit log (§1.8) — the authoritative who/what/when/why.

EN —
The canonical audit store onto which every individual-affecting operation lands a who/what/when/why
record (Plan §1.8; §1.0 fields + dual timestamp). It is the authoritative sink for new operations and for
the **read path** (``recall`` / ``rejected:rbac``) that §1.5/§1.6 deferred here, and it **reconciles** the
forerunners by import: the §1.5 ``governance.audit.AuditLog`` rows (same shape) and the §1.7 ``Transition``
log (mapped to ``action="transition"``). It is append-only (no update/delete) and independent of the
business-table transaction, so a ``rejected:*`` operation still leaves a trace. No event sourcing (PRD §13.1).

中文 —
规范审计存储，每个影响个人的操作都在此落下一条 who/what/when/why 记录（计划 §1.8；§1.0 字段 + 双时间戳）。它是新操作与
**读路径**（``recall`` / ``rejected:rbac``，§1.5/§1.6 推迟至此）的权威落点，并以导入方式**对账**先行者：§1.5
``governance.audit.AuditLog`` 行（同形态）与 §1.7 ``Transition`` 日志（映射为 ``action="transition"``）。它仅追加
（无更新/删除）且独立于业务表事务，故 ``rejected:*`` 操作仍留痕。无事件溯源（PRD §13.1）。
"""
from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional


@dataclass
class AuditRecord:
    """One canonical audit row (the §1.0 who/what/when/why, dual timestamp).

    EN: Attributes: actor; action; target_key; at_monotonic; at_wall (ISO-8601 UTC); reason; result.
    中文：属性：actor；action；target_key；at_monotonic；at_wall（ISO-8601 UTC）；reason；result。
    """

    actor: str
    action: str
    target_key: str
    at_monotonic: float
    at_wall: str
    reason: str
    result: str


class AuditStore:
    """Append-only canonical audit over a migrated SQLite connection (the ``audit_log`` table).

    EN —
    Construct over the canonical connection (``CanonicalStore`` shares its conn; the ``audit_log`` table is
    created by the migration). ``record`` stamps the dual timestamp; ``query`` is the forensics read;
    ``import_governance_audit`` / ``import_transitions`` fold the forerunners in. No mutation API.

    中文 —
    在已迁移的规范连接上构造（``CanonicalStore`` 共享其连接；``audit_log`` 表由迁移创建）。``record`` 打双时间戳；
    ``query`` 为取证读取；``import_governance_audit`` / ``import_transitions`` 折入先行者。无修改 API。
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        """Wrap a migrated connection (assumes ``audit_log`` exists).

        EN: Args: conn. 中文：参数：conn。
        """
        self._conn = conn

    def _insert(self, r: AuditRecord) -> None:
        """Insert a record verbatim (used by ``record`` and the import adapters).

        EN: Args: r. Returns: None. 中文：参数：r。返回：None。
        """
        self._conn.execute(
            "INSERT INTO audit_log (actor, action, target_key, at_monotonic, at_wall, reason, result) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (r.actor, r.action, r.target_key, r.at_monotonic, r.at_wall, r.reason, r.result),
        )
        self._conn.commit()

    def record(self, actor: str, action: str, target_key: str, *, reason: str = "", result: str = "ok") -> None:
        """Append one audit row, stamping the dual timestamp (monotonic + wall).

        EN: Args: actor; action (incl. read-path ``recall`` / ``rejected:rbac``); target_key; reason; result.
            Returns: None. 中文：参数：actor；action（含读路径 ``recall`` / ``rejected:rbac``）；target_key；reason；result。返回：None。
        """
        self._insert(AuditRecord(actor, action, target_key, time.monotonic(),
                                 datetime.now(timezone.utc).isoformat(), reason, result))

    def query(self, *, target_key: Optional[str] = None, actor: Optional[str] = None,
              action: Optional[str] = None, result_prefix: Optional[str] = None) -> List[AuditRecord]:
        """Read audit rows in insertion order, filtered by any of target_key / actor / action / result prefix.

        EN: Args: the optional filters. Returns: matching ``AuditRecord``s, oldest first.
        中文：参数：可选过滤。返回：匹配的 ``AuditRecord``，最早在前。
        """
        sql = "SELECT actor, action, target_key, at_monotonic, at_wall, reason, result FROM audit_log"
        clauses: List[str] = []
        params: List[str] = []
        if target_key is not None:
            clauses.append("target_key = ?")
            params.append(target_key)
        if actor is not None:
            clauses.append("actor = ?")
            params.append(actor)
        if action is not None:
            clauses.append("action = ?")
            params.append(action)
        if result_prefix is not None:
            clauses.append("result LIKE ?")
            params.append(result_prefix + "%")
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY id"
        return [AuditRecord(*row) for row in self._conn.execute(sql, params).fetchall()]

    def import_governance_audit(self, governance_audit_log) -> int:
        """Import the §1.5 governance ``AuditLog`` rows into the canonical store (same shape).

        EN: Args: governance_audit_log (a §1.5 ``AuditLog``). Returns: the number of rows imported.
        中文：参数：governance_audit_log（§1.5 ``AuditLog``）。返回：导入行数。
        """
        rows = governance_audit_log.query()
        for r in rows:
            self._insert(AuditRecord(r.actor, r.action, r.target_key, r.at_monotonic, r.at_wall, r.reason, r.result))
        return len(rows)

    def import_transitions(self, transitions) -> int:
        """Import §1.7 ``Transition`` records, mapping each to a canonical ``action="transition"`` row.

        EN —
        Args: transitions (an iterable of §1.7 ``Transition`` — duck-typed: instance_id/from_state/to_state/
        trigger/at/actor). Returns: the count imported. Historical transitions predate the dual timestamp,
        so ``at_monotonic`` is 0.0 (intra-source order preserved by insertion order; ``at_wall`` carried).

        中文 —
        参数：transitions（§1.7 ``Transition`` 可迭代——鸭子类型：instance_id/from_state/to_state/trigger/at/actor）。返回：
        导入数。历史转移早于双时间戳，故 ``at_monotonic`` 为 0.0（源内顺序由插入顺序保留；``at_wall`` 沿用）。
        """
        count = 0
        for t in transitions:
            self._insert(AuditRecord(t.actor, "transition", t.instance_id, 0.0, t.at,
                                     f"{t.from_state}->{t.to_state}:{t.trigger}", "ok"))
            count += 1
        return count


__all__ = ["AuditRecord", "AuditStore"]
