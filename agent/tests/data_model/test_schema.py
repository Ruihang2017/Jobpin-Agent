"""Tests for ``data/schema.py`` — canonical entity dataclasses + DDL presence.

EN — the M1–M3 entities construct with tenant/org placeholders and skills; every subset table + the seam
tables have CREATE DDL. 中文 — M1–M3 实体可用租户/组织占位与技能构造；每张子集表 + 接缝表均有 CREATE DDL。
"""
from jobpin_agent.data.schema import DEFAULT_TENANT, TABLES, Candidate, MemoryRecord


def test_entities_and_ddl_present():
    """A Candidate carries the placeholders + fields; all M1–M3 tables + seam tables have DDL.

    EN. 中文。
    """
    c = Candidate("cand_x", DEFAULT_TENANT, "apac", name="Ada", skills=["go"], years=8,
                  location="Sydney", work_rights=True, consent_status="granted",
                  memory_key="acme:apac:candidate:cand_x")
    assert c.candidate_id == "cand_x" and c.tenant_id == "acme"
    for t in ("candidate", "job", "application", "interview", "consent", "org", "user", "memory_record", "audit_log"):
        assert t in TABLES and TABLES[t].lstrip().upper().startswith("CREATE TABLE")


def test_memory_record_fields():
    """MemoryRecord carries memory_key + store_kind + governance labels (the §1.4/§1.5 seam).

    EN. 中文。
    """
    m = MemoryRecord("acme:apac:candidate:cand_x", "vector", provenance="cv#1",
                     consent_label="legitimate_interest", retention_policy="not_hired_180d")
    assert m.store_kind == "vector" and m.consent_label == "legitimate_interest"
