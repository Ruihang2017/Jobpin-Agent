"""Tests for ``governance/audit.py`` — append-only log, dual timestamp, filtered query.

EN — Records read back in order with both timestamps; filtering by action/target works; there is no
mutation API. 中文 — 记录按序读回且两种时间戳齐备；按 action/target 过滤有效；无修改 API。
"""
from jobpin_agent.governance.audit import AuditLog


def test_record_and_query_dual_timestamp():
    """Two records read back in order, with monotonic + wall timestamps, and filter correctly.

    EN: record + query. 中文：record + query。
    """
    log = AuditLog()
    log.record("recruiter:alice", "write:add", "acme:apac:org:policy", reason="rubric", result="ok")
    log.record("recruiter:alice", "write:add", "acme:apac:org:x", result="rejected:no_provenance")
    rows = log.query()
    assert len(rows) == 2
    assert rows[0].at_wall and rows[0].at_monotonic > 0
    rej = log.query(action="write:add")
    assert any(r.result == "rejected:no_provenance" for r in rej)
    one = log.query(target_key="acme:apac:org:policy")
    assert len(one) == 1 and one[0].result == "ok"


def test_append_only_has_no_mutation_api():
    """The audit log exposes no delete/update method (append-only by construction).

    EN: no mutation API. 中文：无修改 API。
    """
    log = AuditLog()
    assert not hasattr(log, "delete")
    assert not hasattr(log, "update")
