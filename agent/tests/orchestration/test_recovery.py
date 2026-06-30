"""Tests for ``orchestration/recovery.py`` — the crash-recovery loader returns only non-terminal instances.

EN — recover returns RUNNING / SUSPENDED instances, not DONE. 中文 — recover 返回 RUNNING / SUSPENDED 实例，而非 DONE。
"""
from jobpin_agent.orchestration.recovery import recover
from jobpin_agent.orchestration.state_machine import ProcessInstance, Status
from jobpin_agent.orchestration.store import OrchestrationStore


def test_recover_returns_only_non_terminal():
    """recover yields the resumable (non-terminal) instances.

    EN. 中文。
    """
    s = OrchestrationStore()
    s.save_instance(ProcessInstance("a", "p", "x", Status.RUNNING))
    s.save_instance(ProcessInstance("b", "p", "y", Status.DONE))
    s.save_instance(ProcessInstance("c", "p", "z", Status.SUSPENDED))
    assert {i.instance_id for i in recover(s)} == {"a", "c"}
