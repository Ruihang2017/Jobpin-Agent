from jobpin_agent.core.agent_loop import Agent
from jobpin_agent.core.delegation import delegate
from jobpin_agent.core.messages import ModelResponse
from jobpin_agent.core.model.fake_provider import FakeProvider
from jobpin_agent.core.session_store import SessionStore
from jobpin_agent.core.tools import ToolRegistry


class RecordingHooks:
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
