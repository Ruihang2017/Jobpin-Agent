"""Tests for sub-agent delegation.

EN —
Confirms the delegation invariant: the child runs skip_memory (its own NoOpHooks),
and the parent observes the result via ``on_delegation``.
中文 —
确认委派不变量：子代理以 skip_memory 运行（其自有 NoOpHooks），父代理经 ``on_delegation`` 观察结果。
"""
from jobpin_agent.core.agent_loop import Agent
from jobpin_agent.core.delegation import delegate
from jobpin_agent.core.messages import ModelResponse
from jobpin_agent.core.model.fake_provider import FakeProvider
from jobpin_agent.core.session_store import SessionStore
from jobpin_agent.core.tools import ToolRegistry


class RecordingHooks:
    """A ``MemoryHooks`` stub recording parent prefetch + delegation observations.

    EN: ``prefetched`` proves the child does NOT use the parent's hooks; ``delegations``
    proves the parent observed the child's result.
    中文：``prefetched`` 证明子代理不使用父代理钩子；``delegations`` 证明父代理观察到子代理结果。
    """

    def __init__(self):
        self.delegations = []
        self.prefetched = []

    def prefetch(self, q, session_id):
        self.prefetched.append(q)
        return ""

    def after_turn(self, s, m):
        return None

    def on_delegation(self, task, result, child):
        self.delegations.append((task, result, child))

    def on_session_switch(self, *a):
        return None

    def on_pre_compress(self, m):
        return ""


def test_delegate_runs_child_skip_memory_and_parent_observes():
    """Child runs without the parent's hooks; parent observes the child result.

    EN: The child returns its answer; ``on_delegation`` fires once with that result;
    the parent's ``prefetch`` is never called by the child (skip_memory).
    中文：子代理返回其答复；``on_delegation`` 以该结果触发一次；子代理从不调用父代理的 ``prefetch``（skip_memory）。
    """
    h = RecordingHooks()
    store = SessionStore(hooks=h)
    parent = Agent(FakeProvider([ModelResponse(text="ignored")]), ToolRegistry(), store, hooks=h)
    store.create_session("parent")
    child_provider = FakeProvider([ModelResponse(text="child-done")])
    res = delegate(parent, "do subtask", child_provider=child_provider, child_session_id="child", parent_session_id="parent")
    assert res.text == "child-done" and res.child_session_id == "child"
    # parent observed the delegation
    assert h.delegations == [("do subtask", "child-done", "child")]
    # child ran skip_memory: no prefetch recorded (child uses NoOpHooks, not the parent's hooks)
    assert h.prefetched == []
