"""Tests for ``orchestration/state_machine.py`` — start, legal/illegal transitions, HITL, history.

EN — start sets the initial state + logs; a legal transition advances + persists; an illegal one is
rejected; await/resume HITL; the transition history is appended. 中文 — start 设初始状态并记录；合法转移推进并持久化；
非法转移被拒；await/resume HITL；转移历史被追加。
"""
import pytest

from jobpin_agent.orchestration.state_machine import (
    IllegalTransition, ProcessDefinition, ProcessEngine, Status)
from jobpin_agent.orchestration.store import OrchestrationStore


def _defn() -> ProcessDefinition:
    """A toy hiring definition for the engine tests.

    EN: new → screening → {awaiting_review, done}; awaiting_review → {screening, done}.
    中文：new → screening → {awaiting_review, done}；awaiting_review → {screening, done}。
    """
    return ProcessDefinition(
        process_type="toy", initial_state="new",
        transitions={"new": {"screening"}, "screening": {"awaiting_review", "done"},
                     "awaiting_review": {"screening", "done"}},
        hitl_states={"awaiting_review"}, terminal_states={"done"})


def _engine() -> ProcessEngine:
    """Build an engine over an in-memory store with a fixed clock.

    EN: Returns: a ProcessEngine. 中文：返回：ProcessEngine。
    """
    return ProcessEngine(OrchestrationStore(), _defn(), clock=lambda: "t")


def test_start_sets_initial_state_and_logs():
    """start opens the instance at the initial state (RUNNING) and logs a 'start' transition.

    EN. 中文。
    """
    e = _engine()
    inst = e.start("i1", context_ref="cand:x", actor="system")
    assert inst.current_state == "new" and inst.status == Status.RUNNING
    assert e.store.transitions_for("i1")[0].to_state == "new"


def test_legal_transition_advances_and_persists():
    """A declared transition advances the state and persists it.

    EN. 中文。
    """
    e = _engine()
    e.start("i1")
    inst = e.transition("i1", "screening", trigger="advance", actor="alice")
    assert inst.current_state == "screening" and inst.status == Status.RUNNING
    assert e.store.load_instance("i1").current_state == "screening"


def test_illegal_transition_rejected():
    """An undeclared transition raises IllegalTransition (the guardrail).

    EN: new -> done is not declared. 中文：new -> done 未声明。
    """
    e = _engine()
    e.start("i1")
    with pytest.raises(IllegalTransition):
        e.transition("i1", "done", trigger="skip")


def test_await_and_resume_hitl():
    """await_hitl pauses at a HITL state; resume_hitl advances to a terminal state.

    EN: AWAITING_HITL → DONE. 中文：AWAITING_HITL → DONE。
    """
    e = _engine()
    e.start("i1")
    e.transition("i1", "screening", trigger="advance")
    e.await_hitl("i1", to_state="awaiting_review", trigger="need review", actor="alice")
    assert e.store.load_instance("i1").status == Status.AWAITING_HITL
    e.resume_hitl("i1", to_state="done", decision="approve", actor="bob")
    assert e.store.load_instance("i1").status == Status.DONE


def test_transition_history_is_appended():
    """Every transition is appended to the auditable history in order.

    EN. 中文。
    """
    e = _engine()
    e.start("i1")
    e.transition("i1", "screening", trigger="advance")
    assert [t.to_state for t in e.store.transitions_for("i1")] == ["new", "screening"]


def test_fail_sets_terminal_failed():
    """fail marks the instance FAILED and logs a fail transition.

    EN. 中文。
    """
    e = _engine()
    e.start("i1")
    e.fail("i1", reason="unrecoverable", actor="system")
    assert e.store.load_instance("i1").status == Status.FAILED
    assert e.store.transitions_for("i1")[-1].trigger == "fail:unrecoverable"


def test_transition_unknown_instance_rejected():
    """transition on an unknown instance raises IllegalTransition.

    EN: the inst-is-None branch. 中文：inst 为 None 分支。
    """
    e = _engine()
    with pytest.raises(IllegalTransition):
        e.transition("nope", "screening", trigger="advance")


def test_start_on_existing_instance_rejected():
    """start cannot silently re-start a live instance.

    EN: existence guard. 中文：存在性守卫。
    """
    e = _engine()
    e.start("i1")
    with pytest.raises(IllegalTransition):
        e.start("i1")


def test_fail_from_terminal_rejected():
    """fail on a DONE instance raises (do not flip a terminal outcome).

    EN: terminal guard. 中文：终止守卫。
    """
    e = _engine()
    e.start("i1")
    e.transition("i1", "screening", trigger="advance")
    e.transition("i1", "done", trigger="finish")
    assert e.store.load_instance("i1").status == Status.DONE
    with pytest.raises(IllegalTransition):
        e.fail("i1", reason="too late")


def test_await_hitl_to_non_hitl_state_rejected():
    """await_hitl refuses a to_state that is not a declared hitl_state (name must not lie).

    EN. 中文。
    """
    e = _engine()
    e.start("i1")
    with pytest.raises(IllegalTransition):
        e.await_hitl("i1", to_state="screening", trigger="oops")  # screening is not a hitl_state


def test_definition_rejects_state_class_overlap():
    """ProcessDefinition raises if a state is in two of hitl/suspend/terminal.

    EN: disjointness validation. 中文：互斥校验。
    """
    with pytest.raises(ValueError):
        ProcessDefinition("bad", "a", transitions={"a": {"b"}}, hitl_states={"b"}, terminal_states={"b"})
