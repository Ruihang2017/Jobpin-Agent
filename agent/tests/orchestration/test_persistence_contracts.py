"""The three Layer B persistence-contract acceptance tests (§1.7 exit criteria) — toy process over a file DB.

EN — ① crash recovery (kill → fresh engine over the same file → recover + resume), ② cross-day pause/resume
(suspend → resume later, context intact, no wall-clock assumption), ③ external side-effect idempotency
(retry after restart → effect sent exactly once). 中文 — ① 崩溃恢复，② 跨天暂停/恢复（上下文完整，无墙钟假设），
③ 外部副作用幂等（重启后重试 → 副作用恰发一次）。
"""
from jobpin_agent.orchestration.idempotency import IdempotencyStore
from jobpin_agent.orchestration.recovery import recover
from jobpin_agent.orchestration.state_machine import ProcessDefinition, ProcessEngine, Status
from jobpin_agent.orchestration.store import OrchestrationStore


def _hiring_defn() -> ProcessDefinition:
    """A toy hiring process: new → screening → awaiting_review → offer.

    EN. 中文。
    """
    return ProcessDefinition(
        process_type="hiring", initial_state="new",
        transitions={"new": {"screening"}, "screening": {"awaiting_review"},
                     "awaiting_review": {"offer"}, "offer": set()},
        hitl_states={"awaiting_review"}, terminal_states={"offer"})


def test_contract1_crash_recovery(tmp_path):
    """① Advance to awaiting_hitl, kill the engine, rebuild over the same file, recover + resume to done.

    EN: no state loss, no restart-from-zero. 中文：无状态丢失、不从零重启。
    """
    db = str(tmp_path / "orch.db")
    e = ProcessEngine(OrchestrationStore(db), _hiring_defn())
    e.start("i1", context_ref="cand:7f3a")
    e.transition("i1", "screening", trigger="advance")
    e.await_hitl("i1", to_state="awaiting_review", trigger="need review", actor="alice")
    del e  # "kill" the process

    e2 = ProcessEngine(OrchestrationStore(db), _hiring_defn())  # fresh engine over the SAME file
    resumed = recover(e2.store)
    assert [(i.instance_id, i.status) for i in resumed] == [("i1", Status.AWAITING_HITL)]
    assert e2.store.load_instance("i1").context_ref == "cand:7f3a"  # context intact
    e2.resume_hitl("i1", to_state="offer", decision="approve", actor="bob")
    assert e2.store.load_instance("i1").status == Status.DONE


def test_contract2_cross_day_pause_resume(tmp_path):
    """② Suspend awaiting an external event (logical), resume later over a fresh engine, context intact.

    EN: no wall-clock assumption. 中文：无墙钟假设。
    """
    db = str(tmp_path / "orch.db")
    defn = ProcessDefinition(
        process_type="hiring", initial_state="new",
        transitions={"new": {"awaiting_event"}, "awaiting_event": {"done"}, "done": set()},
        suspend_states={"awaiting_event"}, terminal_states={"done"})
    e = ProcessEngine(OrchestrationStore(db), defn)
    e.start("i1", context_ref="cand:x")
    e.suspend("i1", to_state="awaiting_event", trigger="await external event")
    assert e.store.load_instance("i1").status == Status.SUSPENDED

    e2 = ProcessEngine(OrchestrationStore(db), defn)  # arbitrarily long later; the event arrives
    e2.resume("i1", to_state="done", trigger="event arrived")
    assert e2.store.load_instance("i1").status == Status.DONE
    assert e2.store.load_instance("i1").context_ref == "cand:x"  # context intact across the resume


def test_contract3_side_effect_idempotency(tmp_path):
    """③ Retry sending the same email across a restart → the effect fires exactly once.

    EN. 中文。
    """
    db = str(tmp_path / "orch.db")
    calls = []

    def send_email():
        calls.append(1)
        return "msg-1"

    key = "email:req_812:cand_7f3a:offer"
    IdempotencyStore(OrchestrationStore(db)).run_once(key, send_email)
    IdempotencyStore(OrchestrationStore(db)).run_once(key, send_email)  # retry after "restart"
    assert len(calls) == 1
