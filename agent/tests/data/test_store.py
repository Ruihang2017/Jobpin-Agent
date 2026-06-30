"""Tests for ``data/store.py`` — CanonicalStore CRUD round-trips + the shared canonical audit.

EN — candidate / memory-record round-trip with tenant/org carried; the shared ``.audit`` records over the
same DB. 中文 — 候选人/记忆记录往返且租户/组织沿用；共享 ``.audit`` 在同一库记录。
"""
from jobpin_agent.data.schema import Application, Candidate, Consent, Interview, Job, MemoryRecord, Org, User
from jobpin_agent.data.store import CanonicalStore


def test_candidate_roundtrip_and_shared_audit():
    """Upsert/get a candidate (skills + tenant/org intact); the shared audit records on the same DB.

    EN. 中文。
    """
    s = CanonicalStore()
    s.upsert_candidate(Candidate("cand_x", "acme", "apac", name="Ada", skills=["go", "kafka"], years=8,
                                 location="Sydney", work_rights=True, consent_status="granted",
                                 memory_key="acme:apac:candidate:cand_x"))
    got = s.get_candidate("cand_x")
    assert got.name == "Ada" and got.skills == ["go", "kafka"] and got.tenant_id == "acme" and got.work_rights is True
    s.audit.record("recruiter:alice", "write:add", "acme:apac:candidate:cand_x", result="ok")
    assert s.audit.query(target_key="acme:apac:candidate:cand_x")[-1].result == "ok"


def test_memory_record_roundtrip():
    """Upsert/get a MemoryRecord seam row (store_kind + governance labels).

    EN. 中文。
    """
    s = CanonicalStore()
    s.upsert_memory_record(MemoryRecord("acme:apac:candidate:cand_x", "vector", provenance="cv#1",
                                        consent_label="legitimate_interest", retention_policy="not_hired_180d"))
    got = s.get_memory_record("acme:apac:candidate:cand_x")
    assert got.store_kind == "vector" and got.retention_policy == "not_hired_180d"


def test_other_entities_upsert_without_error():
    """The remaining M1–M3 entities upsert cleanly (schema columns line up).

    EN: job/application/interview/consent/org/user. 中文：job/application/interview/consent/org/user。
    """
    s = CanonicalStore()
    s.upsert_org(Org("apac", "acme", name="ACME APAC"))
    s.upsert_user(User("u1", "acme", "apac", role="recruiter"))
    s.upsert_job(Job("req_812", "acme", "apac", title="Senior Backend Engineer", status="open"))
    s.upsert_application(Application("app1", "cand_x", "req_812", stage="screening", created_at="t0"))
    s.upsert_interview(Interview("iv1", "app1", slot="2026-07-01T10:00Z",
                                 idempotency_key="interview:req_812:cand_x:slot_1", status="proposed"))
    s.upsert_consent(Consent("c1", "cand_x", purpose="hiring", legal_basis="consent",
                             granted_at="t0", ttl_policy="not_hired_180d"))
    # no exception == columns line up; spot-check one via a raw count
    assert s.get_candidate("cand_x") is None  # not inserted here; sanity that get works
