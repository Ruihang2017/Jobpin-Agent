"""Minimal candidate structured store (§1.4) — the retrieval/filter fields only.

EN —
The large-volume retrieval layer pairs each candidate's **semantic vectors** (in the vector
store) with a **structured row** of filterable fields (skills / years / location / work rights /
consent status), keyed by ``memory_key``. ``prefetch`` filters here FIRST (RBAC + hard
conditions) and only then runs vector nearest-neighbour over the survivors — avoiding the
"retrieve first, filter later" leak. This is deliberately minimal: the full canonical data model
(all entities, the audit log) is §1.8; §1.4 carries only what retrieval needs.

中文 —
大体量检索层把每个候选人的**语义向量**（在向量库）与一行可过滤字段的**结构化行**（技能 / 年限 / 地点 / 工作权利 /
同意状态）配对，以 ``memory_key`` 为键。``prefetch`` 在此**先**过滤（RBAC + 硬条件），其后才对幸存者做向量近邻——
避免“先检索后过滤”的泄漏。本实现刻意最小：完整规范数据模型（全部实体、审计日志）是 §1.8；§1.4 只承载检索所需。
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional


@dataclass
class CandidateRow:
    """A candidate's filterable structured fields.

    EN —
    Attributes: memory_key (namespace key); name; skills (list); years (int); location;
    work_rights (bool); consent_status (e.g. "granted"/"withdrawn").
    中文 —
    属性：memory_key（命名空间键）；name；skills（列表）；years（整数）；location；work_rights（布尔）；
    consent_status（如 "granted"/"withdrawn"）。
    """

    memory_key: str
    name: str = ""
    skills: List[str] = field(default_factory=list)
    years: int = 0
    location: str = ""
    work_rights: bool = False
    consent_status: str = "unknown"


class CandidateStructuredStore:
    """A SQLite store of ``CandidateRow``s keyed by ``memory_key`` (§1.4).

    EN —
    ``filter`` loads rows and applies a Python predicate (fine at the local scale); ``delete_by_key_prefix``
    powers the §1.5 erasure cascade alongside the vector store.

    中文 —
    ``filter`` 载入行并应用 Python 谓词（在本地规模下足够）；``delete_by_key_prefix`` 与向量库一同支撑 §1.5 擦除级联。
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        """Open (or create) the store and ensure the schema.

        EN: Args: db_path (``:memory:`` for ephemeral).
        中文：参数：db_path（``:memory:`` 为临时）。
        """
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS candidates ("
            "memory_key TEXT PRIMARY KEY, name TEXT, skills TEXT, years INTEGER, "
            "location TEXT, work_rights INTEGER, consent_status TEXT)"
        )
        self._conn.commit()

    def upsert(self, row: CandidateRow) -> None:
        """Insert or replace a candidate row.

        EN: Args: row. 中文：参数：row。
        """
        self._conn.execute(
            "INSERT OR REPLACE INTO candidates VALUES (?, ?, ?, ?, ?, ?, ?)",
            (row.memory_key, row.name, json.dumps(row.skills), row.years,
             row.location, int(row.work_rights), row.consent_status),
        )
        self._conn.commit()

    def get(self, memory_key: str) -> Optional[CandidateRow]:
        """Fetch a candidate by key.

        EN: Args: memory_key. Returns: the row, or None.
        中文：参数：memory_key。返回：行，或 None。
        """
        r = self._conn.execute("SELECT * FROM candidates WHERE memory_key = ?", (memory_key,)).fetchone()
        return _row(r) if r else None

    def filter(self, predicate: Callable[[CandidateRow], bool]) -> List[CandidateRow]:
        """Return rows matching a Python predicate.

        EN: Args: predicate. Returns: matching rows (the allowed set for filter-before-NN).
        中文：参数：predicate。返回：匹配的行（先过滤再近邻的允许集合）。
        """
        return [row for r in self._conn.execute("SELECT * FROM candidates").fetchall() if predicate(row := _row(r))]

    def delete_by_key_prefix(self, prefix: str) -> int:
        """Delete rows whose memory_key == prefix or is nested under ``prefix:`` (erasure cascade).

        EN: Args: prefix. Returns: rows removed.
        中文：参数：prefix。返回：删除行数。
        """
        like = prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + ":%"
        cur = self._conn.execute(
            "DELETE FROM candidates WHERE memory_key = ? OR memory_key LIKE ? ESCAPE '\\'",
            (prefix, like),
        )
        self._conn.commit()
        return cur.rowcount


def _row(r) -> CandidateRow:
    """Rebuild a ``CandidateRow`` from a DB row.

    EN: Args: r (the 7-column tuple). Returns: the row.
    中文：参数：r（7 列元组）。返回：行。
    """
    return CandidateRow(
        memory_key=r[0], name=r[1], skills=json.loads(r[2]), years=r[3],
        location=r[4], work_rights=bool(r[5]), consent_status=r[6],
    )
