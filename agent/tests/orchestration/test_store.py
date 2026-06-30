"""Tests for ``orchestration/store.py`` — instance round-trip, append-only transitions, non-terminal, idempotency.

EN — Save/load an instance; the transition history is append-only + ordered; non-terminal filtering;
idempotency get/put. 中文 — 保存/加载实例；转移历史仅追加且有序；非终止过滤；幂等 get/put。
"""
from jobpin_agent.orchestration.state_machine import ProcessInstance, Status, Transition
from jobpin_agent.orchestration.store import OrchestrationStore


def test_save_load_instance_roundtrip():
    """An instance saves and loads back with all fields; an unknown id is None.

    EN: round-trip. 中文：往返。
    """
    s = OrchestrationStore()
    s.save_instance(ProcessInstance("i1", "hiring", "screening", Status.RUNNING, context_ref="cand:x", updated_at="t0"))
    got = s.load_instance("i1")
    assert got.current_state == "screening" and got.status == Status.RUNNING and got.context_ref == "cand:x"
    assert s.load_instance("nope") is None


def test_transitions_append_only_and_ordered():
    """Transitions read back in insertion order; there is no mutation API.

    EN: append-only + ordered. 中文：仅追加 + 有序。
    """
    s = OrchestrationStore()
    s.append_transition(Transition("i1", "", "screening", "start", "t0", "system"))
    s.append_transition(Transition("i1", "screening", "interview", "advance", "t1", "alice"))
    assert [t.to_state for t in s.transitions_for("i1")] == ["screening", "interview"]
    assert not hasattr(s, "delete_transition") and not hasattr(s, "update_transition")


def test_non_terminal_instances():
    """Only RUNNING / AWAITING_HITL / SUSPENDED instances are returned (not DONE / FAILED).

    EN: non-terminal filter. 中文：非终止过滤。
    """
    s = OrchestrationStore()
    s.save_instance(ProcessInstance("a", "p", "x", Status.RUNNING))
    s.save_instance(ProcessInstance("b", "p", "y", Status.DONE))
    s.save_instance(ProcessInstance("c", "p", "z", Status.AWAITING_HITL))
    assert {i.instance_id for i in s.non_terminal_instances()} == {"a", "c"}


def test_idempotency_get_put():
    """idem_get/idem_put round-trip; a later put overwrites the status/result.

    EN: pending → done. 中文：pending → done。
    """
    s = OrchestrationStore()
    assert s.idem_get("k") is None
    s.idem_put("k", "pending", "")
    s.idem_put("k", "done", "sent")
    row = s.idem_get("k")
    assert row["status"] == "done" and row["result"] == "sent"
