"""Tests for the §1.4 minimal candidate structured store.

EN — upsert/get round-trip; predicate filter; erasure cascade by key prefix.
中文 — upsert/get 往返；谓词过滤；按键前缀擦除级联。
"""
from jobpin_agent.memory.structured import CandidateRow, CandidateStructuredStore


def test_upsert_get_roundtrip():
    """A stored candidate round-trips (skills list preserved).

    EN: get returns the same fields. 中文：get 返回相同字段。
    """
    s = CandidateStructuredStore()
    s.upsert(CandidateRow("acme:apac:candidate:cand_1", name="Ada", skills=["python", "k8s"], years=5,
                          location="Sydney", work_rights=True, consent_status="granted"))
    got = s.get("acme:apac:candidate:cand_1")
    assert got is not None and got.skills == ["python", "k8s"] and got.years == 5 and got.work_rights is True


def test_filter_predicate():
    """filter returns rows matching the Python predicate.

    EN: python AND years>=3 selects only the senior python candidate.
    中文：python 且 years>=3 仅选中资深 python 候选人。
    """
    s = CandidateStructuredStore()
    s.upsert(CandidateRow("acme:apac:candidate:cand_1", skills=["python"], years=5))
    s.upsert(CandidateRow("acme:apac:candidate:cand_2", skills=["python"], years=1))
    s.upsert(CandidateRow("acme:apac:candidate:cand_3", skills=["go"], years=9))
    keys = {r.memory_key for r in s.filter(lambda r: "python" in r.skills and r.years >= 3)}
    assert keys == {"acme:apac:candidate:cand_1"}


def test_delete_by_key_prefix():
    """delete_by_key_prefix removes a subject and returns the count.

    EN: erasing cand_1 removes it; cand_2 stays. 中文：擦除 cand_1 删除之；cand_2 留存。
    """
    s = CandidateStructuredStore()
    s.upsert(CandidateRow("acme:apac:candidate:cand_1"))
    s.upsert(CandidateRow("acme:apac:candidate:cand_2"))
    assert s.delete_by_key_prefix("acme:apac:candidate:cand_1") == 1
    assert s.get("acme:apac:candidate:cand_1") is None and s.get("acme:apac:candidate:cand_2") is not None
