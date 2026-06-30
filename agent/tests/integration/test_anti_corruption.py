"""Tests for the §1.10 anti-corruption layer — external field names translate to §1.8 canonical fields.

EN — Proves the ACL actually maps the fake ATS's differently-named external fields onto §1.8 entities, and
that an unknown kind fails closed.

中文 — 证明 ACL 确实把伪 ATS 命名不同的外部字段映射到 §1.8 实体，且未知 kind 失败即关闭。
"""
import pytest

from jobpin_agent.integration.connectors.fake_ats import FakeATSAntiCorruption, FakeATSConnector
from jobpin_agent.integration.sdk import ExternalRecord


def test_translate_candidate_maps_external_fields():
    """The fake ATS's full_name/skill_tags/ext_id map to Candidate.name/skills/candidate_id. 中文 — 外部字段映射到规范字段。"""
    conn = FakeATSConnector()
    acl = FakeATSAntiCorruption()
    cands = [acl.translate(r) for r in conn.fetch("candidate")]
    ada = next(c for c in cands if c.name == "Ada Lovelace")
    assert ada.candidate_id == "A-1"
    assert "python" in [s.lower() for s in ada.skills]
    assert ada.years == 7 and ada.location == "Sydney"


def test_translate_job_maps_external_fields():
    """The fake ATS's ext_req/req_title map to Job.job_id/title. 中文 — 职位外部字段映射到 Job。"""
    conn = FakeATSConnector()
    acl = FakeATSAntiCorruption()
    jobs = [acl.translate(r) for r in conn.fetch("job")]
    assert jobs[0].job_id == "R-9" and jobs[0].title == "Senior Engineer"


def test_unknown_kind_raises():
    """An unknown external kind fails closed. 中文 — 未知外部 kind 失败即关闭。"""
    acl = FakeATSAntiCorruption()
    with pytest.raises(ValueError):
        acl.translate(ExternalRecord(source="fake-ats", kind="spaceship", raw={}))
