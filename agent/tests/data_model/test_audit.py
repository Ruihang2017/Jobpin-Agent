"""Tests for ``data/audit.py`` — canonical audit (read+write actions, dual timestamp, reconciliation).

EN — write/erase/recall + a rejected op are recorded and queryable (trace-on-failure); append-only; the
§1.5 governance audit + §1.7 transitions import into the canonical store. 中文 — 写/擦除/召回 + 被拒操作均记录且
可查询（失败留痕）；仅追加；§1.5 治理审计 + §1.7 转移可导入规范存储。
"""
import sqlite3

from jobpin_agent.data.audit import AuditStore
from jobpin_agent.data.migrations import LATEST, migrate


def _audit() -> AuditStore:
    """Build a canonical AuditStore over a migrated in-memory DB. EN/中文: migrated audit store."""
    conn = sqlite3.connect(":memory:")
    migrate(conn, LATEST)
    return AuditStore(conn)


def test_record_query_dual_timestamp_and_read_actions():
    """write/erase/recall + a rejected op are recorded with dual timestamps; query filters; append-only.

    EN. 中文。
    """
    a = _audit()
    a.record("dpo:bob", "erase", "acme:apac:candidate:x", reason="APP 11.2", result="ok")
    a.record("alice", "recall", "acme:apac:candidate:x", result="ok")               # read-path (§1.5/§1.6 deferral)
    a.record("alice", "write:add", "acme:apac:org:policy", result="rejected:bias")  # trace-on-failure
    rows = a.query(target_key="acme:apac:candidate:x")
    assert len(rows) == 2 and rows[0].at_wall and rows[0].at_monotonic > 0
    assert {r.result for r in a.query(action="write:add")} == {"rejected:bias"}
    assert [r.action for r in a.query(result_prefix="rejected")] == ["write:add"]
    assert not hasattr(a, "delete") and not hasattr(a, "update")


def test_import_governance_audit_and_transitions():
    """The §1.5 governance audit + §1.7 transitions reconcile into the canonical store and are queryable.

    EN. 中文。
    """
    from jobpin_agent.governance.audit import AuditLog
    from jobpin_agent.orchestration.state_machine import ProcessDefinition, ProcessEngine
    from jobpin_agent.orchestration.store import OrchestrationStore

    gov = AuditLog()
    gov.record("recruiter:alice", "write:add", "acme:apac:org:policy", result="ok")
    osd = OrchestrationStore()
    engine = ProcessEngine(osd, ProcessDefinition("p", "a", {"a": {"b"}, "b": set()}, terminal_states={"b"}))
    engine.start("i1")
    engine.transition("i1", "b", trigger="advance")

    a = _audit()
    assert a.import_governance_audit(gov) == 1
    assert a.import_transitions(osd.transitions_for("i1")) == 2  # start + advance
    assert any(r.action == "transition" and r.target_key == "i1" for r in a.query())
    assert any(r.action == "write:add" and r.target_key == "acme:apac:org:policy" for r in a.query())


def test_result_prefix_escapes_like_metacharacters():
    """A result code containing '_' is matched literally by result_prefix (not as a wildcard).

    EN: 'rejected:no_consent' must not be matched by prefix 'rejected:no#consent'-style wildcards.
    中文：'rejected:no_consent' 不应被通配匹配。
    """
    a = _audit()
    a.record("x", "write:add", "k1", result="rejected:no_consent")
    a.record("x", "write:add", "k2", result="rejected:noXconsent")  # the '_' as a wildcard would catch this
    rows = a.query(result_prefix="rejected:no_consent")
    assert [r.target_key for r in rows] == ["k1"]   # only the literal match, not the wildcard one


def test_import_is_one_shot_re_import_duplicates():
    """Documented one-shot semantics: re-importing the same source DOUBLES the canonical rows (no dedup).

    EN: locks in the disclosed non-idempotent behaviour. 中文：锁定已披露的非幂等行为。
    """
    from jobpin_agent.governance.audit import AuditLog
    gov = AuditLog()
    gov.record("alice", "write:add", "k", result="ok")
    a = _audit()
    a.import_governance_audit(gov)
    a.import_governance_audit(gov)               # re-import
    assert len(a.query(target_key="k")) == 2     # duplicated (one-shot snapshot, by design)


def test_audit_record_is_thread_safe():
    """The canonical audit can be recorded from another thread (the §1.5 read-path deferral contract).

    EN: check_same_thread=False + lock — concurrent records from a worker thread do not raise and all land.
    中文：check_same_thread=False + 锁——来自工作线程的并发记录不抛错且全部落地。
    """
    import threading
    from jobpin_agent.data.store import CanonicalStore
    s = CanonicalStore()  # opens check_same_thread=False with the shared lock

    def worker():
        for i in range(20):
            s.audit.record("worker", "recall", f"k{i}", result="ok")

    t = threading.Thread(target=worker)
    t.start()
    for i in range(20):
        s.audit.record("main", "recall", f"m{i}", result="ok")
    t.join()
    assert len(s.audit.query(actor="worker")) == 20 and len(s.audit.query(actor="main")) == 20
