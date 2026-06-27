from jobpin_agent.core.agent_loop import Agent
from jobpin_agent.core.messages import Role, ModelResponse, ToolCall
from jobpin_agent.core.model.fake_provider import FakeProvider
from jobpin_agent.core.session_store import SessionStore
from jobpin_agent.core.tools import ToolRegistry, echo_tool
from jobpin_agent.core.tracing import Tracer


def _agent(script, max_iters=8):
    reg = ToolRegistry()
    reg.register(echo_tool())
    store = SessionStore()
    tracer = Tracer()
    agent = Agent(FakeProvider(script), reg, store, tracer=tracer, max_tool_iterations=max_iters)
    sid = store.create_session("s1")
    return agent, store, tracer, sid


def test_plain_answer_path():
    agent, store, tracer, sid = _agent([ModelResponse(text="hello")])
    r = agent.run_turn(sid, "hi")
    assert r.text == "hello" and r.stopped is False
    assert [m.role for m in store.get_messages(sid)] == [Role.USER, Role.ASSISTANT]


def test_single_tool_call_then_answer():
    script = [ModelResponse(tool_calls=[ToolCall("c1", "echo", {"text": "X"})]), ModelResponse(text="done:X")]
    agent, store, tracer, sid = _agent(script)
    r = agent.run_turn(sid, "use echo")
    assert r.text == "done:X" and r.stopped is False
    roles = [m.role for m in store.get_messages(sid)]
    assert roles == [Role.USER, Role.ASSISTANT, Role.TOOL, Role.ASSISTANT]
    assert any(e.kind == "tool_call" for e in tracer.events)


def test_multi_turn_tool_continuation():
    script = [
        ModelResponse(tool_calls=[ToolCall("c1", "echo", {"text": "A"})]),
        ModelResponse(tool_calls=[ToolCall("c2", "echo", {"text": "B"})]),
        ModelResponse(text="final"),
    ]
    agent, store, tracer, sid = _agent(script)
    r = agent.run_turn(sid, "twice")
    assert r.text == "final"
    assert sum(1 for e in tracer.events if e.kind == "tool_call") == 2


def test_stop_condition_on_max_iterations():
    script = [ModelResponse(tool_calls=[ToolCall(f"c{i}", "echo", {"text": "x"})]) for i in range(5)]
    agent, store, tracer, sid = _agent(script, max_iters=2)
    r = agent.run_turn(sid, "loop")
    assert r.stopped is True and r.text is None
    # exactly max_iters tool rounds executed before stopping (no further executions)
    assert sum(1 for e in tracer.events if e.kind == "tool_call") == 2


def test_prefetch_recall_is_fenced_message_not_in_frozen_snapshot():
    """Architect fix: per-turn prefetch recall goes into a fenced <memory-context>
    MESSAGE, never the system-prompt snapshot slot; self.parts is not mutated."""
    from jobpin_agent.core.system_prompt import SystemPromptParts

    class RecallHooks:
        def prefetch(self, query, session_id):
            return "RECALLED-FACT"

        def after_turn(self, s, m):
            return None

        def on_delegation(self, t, r, c):
            return None

        def on_session_switch(self, *a):
            return None

        def on_pre_compress(self, m):
            return ""

    reg = ToolRegistry()
    reg.register(echo_tool())
    store = SessionStore()
    provider = FakeProvider([ModelResponse(text="ok")])
    parts = SystemPromptParts(org_policy="POLICY")
    agent = Agent(provider, reg, store, hooks=RecallHooks(), parts=parts)
    sid = store.create_session("s1")
    agent.run_turn(sid, "hi")

    sent = provider.calls[0]  # messages the model actually received
    system = sent[0]
    assert system.role == Role.SYSTEM
    assert "RECALLED-FACT" not in system.content  # not baked into the frozen snapshot
    assert any("<memory-context>" in m.content and "RECALLED-FACT" in m.content for m in sent)
    assert agent.parts.memory_snapshot == ""  # self.parts never mutated
