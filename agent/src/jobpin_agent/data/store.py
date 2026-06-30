"""CanonicalStore (§1.8) — relational CRUD over the canonical entities + the shared canonical audit.

EN —
The relational source of truth for the M1–M3 entities. On construction it migrates the connection to the
latest schema and exposes ``.audit`` (an ``AuditStore`` over the SAME connection, so entity writes and
their audit rows live in one DB). CRUD is parameterised SQL; ``skills`` is JSON-encoded (as in the §1.4
structured store). This is the canonical store; the §1.4 ``CandidateStructuredStore`` coexists as the
retrieval projection (see ``docs/entity-memory-mapping.md``).

中文 —
M1–M3 实体的关系事实来源。构造时把连接迁移到最新模式并暴露 ``.audit``（在**同一**连接上的 ``AuditStore``，使实体写入与
其审计行同处一库）。CRUD 为参数化 SQL；``skills`` JSON 编码（同 §1.4 结构化存储）。这是规范存储；§1.4
``CandidateStructuredStore`` 作为检索投影并存（见 ``docs/entity-memory-mapping.md``）。
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Optional

from .audit import AuditStore
from .migrations import LATEST, migrate
from .schema import Application, Candidate, Consent, Interview, Job, MemoryRecord, Org, User


class CanonicalStore:
    """The canonical relational store (migrated on open) + a shared ``.audit`` (§1.8).

    EN —
    Construct over ``:memory:`` (tests) or a file path. ``.audit`` is an ``AuditStore`` over the same
    connection. Each ``upsert_*`` is an INSERT OR REPLACE; each ``get_*`` returns the typed dataclass or None.

    中文 —
    在 ``:memory:``（测试）或文件路径上构造。``.audit`` 是同一连接上的 ``AuditStore``。每个 ``upsert_*`` 为 INSERT OR
    REPLACE；每个 ``get_*`` 返回类型化数据类或 None。
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        """Open the store, migrate to the latest schema, and wire the shared audit.

        EN: Args: db_path. 中文：参数：db_path。
        """
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        migrate(self._conn, LATEST)
        self.audit = AuditStore(self._conn)

    # -- Candidate --------------------------------------------------------
    def upsert_candidate(self, c: Candidate) -> None:
        """Insert or replace a candidate (the canonical source of truth).

        EN: Args: c. 中文：参数：c。
        """
        self._conn.execute(
            "INSERT OR REPLACE INTO candidate VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (c.candidate_id, c.tenant_id, c.org_id, c.name, json.dumps(c.skills), c.years,
             c.location, int(c.work_rights), c.consent_status, c.memory_key),
        )
        self._conn.commit()

    def get_candidate(self, candidate_id: str) -> Optional[Candidate]:
        """Fetch a candidate by id.

        EN: Args: candidate_id. Returns: the ``Candidate`` or None. 中文：参数：candidate_id。返回：``Candidate`` 或 None。
        """
        r = self._conn.execute("SELECT * FROM candidate WHERE candidate_id=?", (candidate_id,)).fetchone()
        if r is None:
            return None
        return Candidate(r[0], r[1], r[2], name=r[3], skills=json.loads(r[4]), years=r[5],
                         location=r[6], work_rights=bool(r[7]), consent_status=r[8], memory_key=r[9])

    # -- Job / Application / Interview / Consent / Org / User -------------
    def upsert_job(self, j: Job) -> None:
        """Insert or replace a job. EN: Args: j. 中文：参数：j。"""
        self._conn.execute("INSERT OR REPLACE INTO job VALUES (?, ?, ?, ?, ?)",
                           (j.job_id, j.tenant_id, j.org_id, j.title, j.status))
        self._conn.commit()

    def upsert_application(self, a: Application) -> None:
        """Insert or replace an application. EN: Args: a. 中文：参数：a。"""
        self._conn.execute("INSERT OR REPLACE INTO application VALUES (?, ?, ?, ?, ?)",
                           (a.application_id, a.candidate_id, a.job_id, a.stage, a.created_at))
        self._conn.commit()

    def upsert_interview(self, i: Interview) -> None:
        """Insert or replace an interview. EN: Args: i. 中文：参数：i。"""
        self._conn.execute("INSERT OR REPLACE INTO interview VALUES (?, ?, ?, ?, ?)",
                           (i.interview_id, i.application_id, i.slot, i.idempotency_key, i.status))
        self._conn.commit()

    def upsert_consent(self, c: Consent) -> None:
        """Insert or replace a consent record. EN: Args: c. 中文：参数：c。"""
        self._conn.execute("INSERT OR REPLACE INTO consent VALUES (?, ?, ?, ?, ?, ?)",
                           (c.consent_id, c.candidate_id, c.purpose, c.legal_basis, c.granted_at, c.ttl_policy))
        self._conn.commit()

    def upsert_org(self, o: Org) -> None:
        """Insert or replace an org. EN: Args: o. 中文：参数：o。"""
        self._conn.execute("INSERT OR REPLACE INTO org VALUES (?, ?, ?)", (o.org_id, o.tenant_id, o.name))
        self._conn.commit()

    def upsert_user(self, u: User) -> None:
        """Insert or replace a user. EN: Args: u. 中文：参数：u。"""
        self._conn.execute("INSERT OR REPLACE INTO user VALUES (?, ?, ?, ?)",
                           (u.user_id, u.tenant_id, u.org_id, u.role))
        self._conn.commit()

    # -- MemoryRecord (the §1.4/§1.5 seam) -------------------------------
    def upsert_memory_record(self, m: MemoryRecord) -> None:
        """Insert or replace a memory-record seam row. EN: Args: m. 中文：参数：m。"""
        self._conn.execute("INSERT OR REPLACE INTO memory_record VALUES (?, ?, ?, ?, ?)",
                           (m.memory_key, m.store_kind, m.provenance, m.consent_label, m.retention_policy))
        self._conn.commit()

    def get_memory_record(self, memory_key: str) -> Optional[MemoryRecord]:
        """Fetch a memory-record seam row by key.

        EN: Args: memory_key. Returns: the ``MemoryRecord`` or None. 中文：参数：memory_key。返回：``MemoryRecord`` 或 None。
        """
        r = self._conn.execute("SELECT * FROM memory_record WHERE memory_key=?", (memory_key,)).fetchone()
        return None if r is None else MemoryRecord(r[0], r[1], provenance=r[2], consent_label=r[3], retention_policy=r[4])

    def close(self) -> None:
        """Close the connection. EN: Returns: None. 中文：返回：None。"""
        self._conn.close()


__all__ = ["CanonicalStore"]
