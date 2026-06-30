"""CanonicalStore (§1.8) — relational CRUD over the canonical entities + the shared canonical audit.

EN —
The relational source of truth for the M1–M3 entities. On construction it migrates the connection to the
latest schema and exposes ``.audit`` (an ``AuditStore`` over the SAME connection, so entity writes and
their audit rows live in one DB). The connection is opened ``check_same_thread=False`` and ALL access
(CRUD + audit) is serialised by one ``threading.Lock`` — so the §1.3 background ``mem-sync`` worker can
record read-path audit (the §1.5 deferral) while the main thread does entity CRUD, without racing the
shared connection. CRUD is parameterised SQL; ``skills`` is JSON-encoded (as in the §1.4 structured store).
This is the canonical store; the §1.4 ``CandidateStructuredStore`` coexists as the retrieval projection
(see ``docs/entity-memory-mapping.md``).

中文 —
M1–M3 实体的关系事实来源。构造时把连接迁移到最新模式并暴露 ``.audit``（在**同一**连接上的 ``AuditStore``，使实体写入与
其审计行同处一库）。连接以 ``check_same_thread=False`` 打开，且对其所有访问（CRUD + 审计）由一把 ``threading.Lock`` 串行
——故 §1.3 后台 ``mem-sync`` worker 可记录读路径审计（§1.5 推迟），同时主线程做实体 CRUD，而不与共享连接竞争。CRUD 为
参数化 SQL；``skills`` JSON 编码（同 §1.4 结构化存储）。这是规范存储；§1.4 ``CandidateStructuredStore`` 作检索投影并存
（见 ``docs/entity-memory-mapping.md``）。
"""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import List, Optional

from .audit import AuditStore
from .migrations import LATEST, migrate
from .schema import Application, Candidate, Consent, Interview, Job, MemoryRecord, Org, User


class CanonicalStore:
    """The canonical relational store (migrated on open) + a shared, thread-safe ``.audit`` (§1.8).

    EN —
    Construct over ``:memory:`` (tests) or a file path. ``.audit`` is an ``AuditStore`` over the same
    connection + lock. Each ``upsert_*`` is an INSERT OR REPLACE; each ``get_*`` returns the typed
    dataclass or None — all serialised by the shared lock.

    中文 —
    在 ``:memory:``（测试）或文件路径上构造。``.audit`` 是同一连接 + 锁上的 ``AuditStore``。每个 ``upsert_*`` 为 INSERT
    OR REPLACE；每个 ``get_*`` 返回类型化数据类或 None——皆由共享锁串行。
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        """Open the store, migrate to the latest schema, and wire the shared thread-safe audit.

        EN: Args: db_path. 中文：参数：db_path。
        """
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock:
            migrate(self._conn, LATEST)
        self.audit = AuditStore(self._conn, lock=self._lock)

    def _write(self, sql: str, params: tuple) -> None:
        """Run a parameterised write under the shared lock.

        EN: Args: sql; params. Returns: None. 中文：参数：sql；params。返回：None。
        """
        with self._lock:
            self._conn.execute(sql, params)
            self._conn.commit()

    def _read_one(self, sql: str, params: tuple):
        """Run a parameterised single-row read under the shared lock.

        EN: Args: sql; params. Returns: the row tuple or None. 中文：参数：sql；params。返回：行元组或 None。
        """
        with self._lock:
            return self._conn.execute(sql, params).fetchone()

    def _read_all(self, sql: str, params: tuple) -> list:
        """Run a parameterised multi-row read under the shared lock.

        EN: Args: sql; params. Returns: the row tuples. 中文：参数：sql；params。返回：行元组列表。
        """
        with self._lock:
            return self._conn.execute(sql, params).fetchall()

    # -- Candidate --------------------------------------------------------
    def upsert_candidate(self, c: Candidate) -> None:
        """Insert or replace a candidate (the canonical source of truth). EN: Args: c. 中文：参数：c。"""
        self._write("INSERT OR REPLACE INTO candidate VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (c.candidate_id, c.tenant_id, c.org_id, c.name, json.dumps(c.skills), c.years,
                     c.location, int(c.work_rights), c.consent_status, c.memory_key))

    def get_candidate(self, candidate_id: str) -> Optional[Candidate]:
        """Fetch a candidate by id. EN: Returns: the ``Candidate`` or None. 中文：返回：``Candidate`` 或 None。"""
        r = self._read_one("SELECT * FROM candidate WHERE candidate_id=?", (candidate_id,))
        if r is None:
            return None
        return Candidate(r[0], r[1], r[2], name=r[3], skills=json.loads(r[4]), years=r[5],
                         location=r[6], work_rights=bool(r[7]), consent_status=r[8], memory_key=r[9])

    # -- Job / Application / Interview / Consent / Org / User -------------
    def upsert_job(self, j: Job) -> None:
        """Insert or replace a job. EN: Args: j. 中文：参数：j。"""
        self._write("INSERT OR REPLACE INTO job VALUES (?, ?, ?, ?, ?)",
                    (j.job_id, j.tenant_id, j.org_id, j.title, j.status))

    def get_job(self, job_id: str) -> Optional[Job]:
        """Fetch a job by id. EN: Returns: the ``Job`` or None. 中文：返回：``Job`` 或 None。"""
        r = self._read_one("SELECT * FROM job WHERE job_id=?", (job_id,))
        return None if r is None else Job(r[0], r[1], r[2], title=r[3], status=r[4])

    def upsert_application(self, a: Application) -> None:
        """Insert or replace an application. EN: Args: a. 中文：参数：a。"""
        self._write("INSERT OR REPLACE INTO application VALUES (?, ?, ?, ?, ?)",
                    (a.application_id, a.candidate_id, a.job_id, a.stage, a.created_at))

    def get_application(self, application_id: str) -> Optional[Application]:
        """Fetch an application by id. EN: Returns: the ``Application`` or None. 中文：返回：``Application`` 或 None。"""
        r = self._read_one("SELECT * FROM application WHERE application_id=?", (application_id,))
        return None if r is None else Application(r[0], r[1], r[2], stage=r[3], created_at=r[4])

    def upsert_interview(self, i: Interview) -> None:
        """Insert or replace an interview. EN: Args: i. 中文：参数：i。"""
        self._write("INSERT OR REPLACE INTO interview VALUES (?, ?, ?, ?, ?)",
                    (i.interview_id, i.application_id, i.slot, i.idempotency_key, i.status))

    def get_interview(self, interview_id: str) -> Optional[Interview]:
        """Fetch an interview by id. EN: Returns: the ``Interview`` or None. 中文：返回：``Interview`` 或 None。"""
        r = self._read_one("SELECT * FROM interview WHERE interview_id=?", (interview_id,))
        return None if r is None else Interview(r[0], r[1], slot=r[2], idempotency_key=r[3], status=r[4])

    def upsert_consent(self, c: Consent) -> None:
        """Insert or replace a consent record. EN: Args: c. 中文：参数：c。"""
        self._write("INSERT OR REPLACE INTO consent VALUES (?, ?, ?, ?, ?, ?)",
                    (c.consent_id, c.candidate_id, c.purpose, c.legal_basis, c.granted_at, c.ttl_policy))

    def get_consent(self, consent_id: str) -> Optional[Consent]:
        """Fetch a consent record by id (the lawful-basis anchor — APP 12/13 access).

        EN: Returns: the ``Consent`` or None. 中文：返回：``Consent`` 或 None。
        """
        r = self._read_one("SELECT * FROM consent WHERE consent_id=?", (consent_id,))
        return None if r is None else Consent(r[0], r[1], purpose=r[2], legal_basis=r[3],
                                              granted_at=r[4], ttl_policy=r[5])

    def consents_for_candidate(self, candidate_id: str) -> List[Consent]:
        """List a candidate's consent records (for a data-subject access request).

        EN: Args: candidate_id. Returns: the consent rows. 中文：参数：candidate_id。返回：同意记录。
        """
        rows = self._read_all("SELECT * FROM consent WHERE candidate_id=? ORDER BY consent_id", (candidate_id,))
        return [Consent(r[0], r[1], purpose=r[2], legal_basis=r[3], granted_at=r[4], ttl_policy=r[5]) for r in rows]

    def upsert_org(self, o: Org) -> None:
        """Insert or replace an org. EN: Args: o. 中文：参数：o。"""
        self._write("INSERT OR REPLACE INTO org VALUES (?, ?, ?)", (o.org_id, o.tenant_id, o.name))

    def get_org(self, org_id: str) -> Optional[Org]:
        """Fetch an org by id. EN: Returns: the ``Org`` or None. 中文：返回：``Org`` 或 None。"""
        r = self._read_one("SELECT * FROM org WHERE org_id=?", (org_id,))
        return None if r is None else Org(r[0], r[1], name=r[2])

    def upsert_user(self, u: User) -> None:
        """Insert or replace a user. EN: Args: u. 中文：参数：u。"""
        self._write("INSERT OR REPLACE INTO user VALUES (?, ?, ?, ?)", (u.user_id, u.tenant_id, u.org_id, u.role))

    def get_user(self, user_id: str) -> Optional[User]:
        """Fetch a user by id (the audit actor / RBAC principal source). EN: Returns: ``User`` or None. 中文：返回：``User`` 或 None。"""
        r = self._read_one("SELECT * FROM user WHERE user_id=?", (user_id,))
        return None if r is None else User(r[0], r[1], r[2], role=r[3])

    # -- MemoryRecord (the §1.4/§1.5 seam) -------------------------------
    def upsert_memory_record(self, m: MemoryRecord) -> None:
        """Insert or replace a memory-record seam row. EN: Args: m. 中文：参数：m。"""
        self._write("INSERT OR REPLACE INTO memory_record VALUES (?, ?, ?, ?, ?)",
                    (m.memory_key, m.store_kind, m.provenance, m.consent_label, m.retention_policy))

    def get_memory_record(self, memory_key: str) -> Optional[MemoryRecord]:
        """Fetch a memory-record seam row by exact key. EN: Returns: ``MemoryRecord`` or None. 中文：返回：``MemoryRecord`` 或 None。"""
        r = self._read_one("SELECT * FROM memory_record WHERE memory_key=?", (memory_key,))
        return None if r is None else MemoryRecord(r[0], r[1], provenance=r[2], consent_label=r[3], retention_policy=r[4])

    def memory_records_under(self, prefix: str) -> List[MemoryRecord]:
        """List memory-record seam rows whose ``memory_key`` equals or is nested under ``prefix`` (data-subject query).

        EN —
        Backs the ``Candidate → MemoryRecord`` join in the entity-memory mapping doc: given a namespace
        prefix (e.g. ``acme:apac:candidate:cand_7f3a``) it returns every memory record about that subject,
        across the file/vector/struct stores, with their governance labels. LIKE metacharacters in the
        prefix are escaped.
        Args: prefix. Returns: the matching ``MemoryRecord``s.

        中文 —
        支撑实体-记忆映射文档中的 ``Candidate → MemoryRecord`` 连接：给定命名空间前缀（如
        ``acme:apac:candidate:cand_7f3a``），返回关于该主体、跨 file/vector/struct 存储的每条记忆记录及其治理标签。
        前缀中的 LIKE 元字符被转义。参数：prefix。返回：匹配的 ``MemoryRecord``。
        """
        like = prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + ":%"
        rows = self._read_all(
            "SELECT * FROM memory_record WHERE memory_key=? OR memory_key LIKE ? ESCAPE '\\' ORDER BY memory_key",
            (prefix, like))
        return [MemoryRecord(r[0], r[1], provenance=r[2], consent_label=r[3], retention_policy=r[4]) for r in rows]

    def close(self) -> None:
        """Close the connection. EN: Returns: None. 中文：返回：None。"""
        with self._lock:
            self._conn.close()


__all__ = ["CanonicalStore"]
