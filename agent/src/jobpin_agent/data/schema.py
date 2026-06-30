"""Canonical entity dataclasses + SQLite DDL (§1.8) — the M1–M3 subset.

EN —
The canonical relational entities for M1–M3 (Plan §1.8 / PRD §11.1), plus the two seam tables
(``AuditRecord`` via ``audit_log``, ``MemoryRecord``). Every business entity carries ``tenant_id`` (a
single-tenant placeholder, kept for Phase-2 multi-tenancy) and ``org_id``. ``TABLES`` (name → CREATE SQL)
is the source the migration runner applies; the dataclasses are the typed shapes the store reads/writes.

中文 —
M1–M3 的规范关系实体（计划 §1.8 / PRD §11.1），外加两张接缝表（``AuditRecord`` 经 ``audit_log``、``MemoryRecord``）。
每个业务实体携带 ``tenant_id``（单租户占位，为第二阶段多租户保留）与 ``org_id``。``TABLES``（名称 → CREATE SQL）是迁移
运行器所应用的来源；数据类是存储读写的类型化形态。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from ..governance.namespace import DEFAULT_ORG, DEFAULT_TENANT  # single source of the placeholders

__all__ = [
    "DEFAULT_TENANT", "DEFAULT_ORG", "TABLES",
    "Candidate", "Job", "Application", "Interview", "Consent", "Org", "User", "MemoryRecord",
]


@dataclass
class Candidate:
    """A candidate (the canonical source of truth; the §1.4 structured store is its retrieval projection).

    EN: Attributes per Plan §1.8: candidate_id; tenant_id; org_id; name; skills; years; location;
        work_rights; consent_status; memory_key. 中文：属性见计划 §1.8。
    """

    candidate_id: str
    tenant_id: str = DEFAULT_TENANT
    org_id: str = DEFAULT_ORG
    name: str = ""
    skills: List[str] = field(default_factory=list)
    years: int = 0
    location: str = ""
    work_rights: bool = False
    consent_status: str = "unknown"
    memory_key: str = ""


@dataclass
class Job:
    """A job / requisition.

    EN: Attributes: job_id; tenant_id; org_id; title; status. 中文：属性：job_id；tenant_id；org_id；title；status。
    """

    job_id: str
    tenant_id: str = DEFAULT_TENANT
    org_id: str = DEFAULT_ORG
    title: str = ""
    status: str = "open"


@dataclass
class Application:
    """A candidate's application to a job.

    EN: Attributes: application_id; candidate_id; job_id; stage; created_at.
    中文：属性：application_id；candidate_id；job_id；stage；created_at。
    """

    application_id: str
    candidate_id: str
    job_id: str
    stage: str = "new"
    created_at: str = ""


@dataclass
class Interview:
    """An interview slot for an application (carries the §1.7 idempotency_key for the scheduling side effect).

    EN: Attributes: interview_id; application_id; slot; idempotency_key; status.
    中文：属性：interview_id；application_id；slot；idempotency_key；status。
    """

    interview_id: str
    application_id: str
    slot: str = ""
    idempotency_key: str = ""
    status: str = "proposed"


@dataclass
class Consent:
    """A candidate's consent record (the lawful-basis anchor — APP 3/5/6).

    EN: Attributes: consent_id; candidate_id; purpose; legal_basis; granted_at; ttl_policy.
    中文：属性：consent_id；candidate_id；purpose；legal_basis；granted_at；ttl_policy。
    """

    consent_id: str
    candidate_id: str
    purpose: str = ""
    legal_basis: str = ""
    granted_at: str = ""
    ttl_policy: str = ""


@dataclass
class Org:
    """An organisation (tenant-scoped).

    EN: Attributes: org_id; tenant_id; name. 中文：属性：org_id；tenant_id；name。
    """

    org_id: str
    tenant_id: str = DEFAULT_TENANT
    name: str = ""


@dataclass
class User:
    """An application user with a role (the audit ``actor`` / RBAC principal source — §1.5/§1.9).

    EN: Attributes: user_id; tenant_id; org_id; role. 中文：属性：user_id；tenant_id；org_id；role。
    """

    user_id: str
    tenant_id: str = DEFAULT_TENANT
    org_id: str = DEFAULT_ORG
    role: str = ""


@dataclass
class MemoryRecord:
    """The seam index of a memory entry across the three stores (ties §1.4/§1.5 to the relational layer).

    EN: Attributes: memory_key; store_kind ∈ {file, vector, struct}; provenance; consent_label;
        retention_policy. 中文：属性：memory_key；store_kind ∈ {file, vector, struct}；provenance；consent_label；
        retention_policy。
    """

    memory_key: str
    store_kind: str
    provenance: str = ""
    consent_label: str = ""
    retention_policy: str = ""


# name → CREATE SQL. The migration runner (data/migrations.py) applies these; the canonical store reads/writes them.
TABLES = {
    "candidate": (
        "CREATE TABLE IF NOT EXISTS candidate (candidate_id TEXT PRIMARY KEY, tenant_id TEXT, org_id TEXT, "
        "name TEXT, skills TEXT, years INTEGER, location TEXT, work_rights INTEGER, consent_status TEXT, memory_key TEXT)"
    ),
    "job": (
        "CREATE TABLE IF NOT EXISTS job (job_id TEXT PRIMARY KEY, tenant_id TEXT, org_id TEXT, title TEXT, status TEXT)"
    ),
    "application": (
        "CREATE TABLE IF NOT EXISTS application (application_id TEXT PRIMARY KEY, candidate_id TEXT, job_id TEXT, "
        "stage TEXT, created_at TEXT)"
    ),
    "interview": (
        "CREATE TABLE IF NOT EXISTS interview (interview_id TEXT PRIMARY KEY, application_id TEXT, slot TEXT, "
        "idempotency_key TEXT, status TEXT)"
    ),
    "consent": (
        "CREATE TABLE IF NOT EXISTS consent (consent_id TEXT PRIMARY KEY, candidate_id TEXT, purpose TEXT, "
        "legal_basis TEXT, granted_at TEXT, ttl_policy TEXT)"
    ),
    "org": "CREATE TABLE IF NOT EXISTS org (org_id TEXT PRIMARY KEY, tenant_id TEXT, name TEXT)",
    "user": "CREATE TABLE IF NOT EXISTS user (user_id TEXT PRIMARY KEY, tenant_id TEXT, org_id TEXT, role TEXT)",
    "memory_record": (
        "CREATE TABLE IF NOT EXISTS memory_record (memory_key TEXT PRIMARY KEY, "
        "store_kind TEXT CHECK(store_kind IN ('file', 'vector', 'struct')), provenance TEXT, "
        "consent_label TEXT, retention_policy TEXT)"
    ),
    "audit_log": (
        "CREATE TABLE IF NOT EXISTS audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, actor TEXT, action TEXT, "
        "target_key TEXT, at_monotonic REAL, at_wall TEXT, reason TEXT, result TEXT)"
    ),
}
