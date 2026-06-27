"""Tests for the agent turn loop.

EN —
Covers the four loop paths (plain / single tool / multi-turn tool / stop) and the
architect-mandated separation of per-turn recall from the frozen system-prompt.
中文 —
覆盖四条循环路径（纯文本 / 单工具 / 多回合工具 / 停止），以及架构师要求的“每回合召回与冻结系统提示分离”。
"""
from jobpin_agent.core.agent_loop import Agent
from jobpin_agent.core.messages import Role, ModelResponse, ToolCall
from jobpin_agent.core.model.fake_provider import FakeProvider
from jobpin_agent.core.session_store import SessionStore
from jobpin_agent.core.tools import ToolRegistry, echo_tool
from jobpin_agent.core.tracing import Tracer


def _agent(script, max_iters=8):
    """Build an Agent wired with echo + a scripted FakeProvider for a test.

    EN: Returns (agent, store, tracer, session_id) ready to run one turn.
    中文：返回 (agent, store, tracer, session_id)，可直接运行一个回合。
    """
    reg = ToolRegistry()
    reg.register(echo_tool())
    store = SessionStore()
    tracer = Tracer()
    agent = Agent(FakeProvider(script), reg, store, tracer=tracer, max_tool_iterations=max_iters)
    sid = store.create_session("s1")
    return agent, store, tracer, sid


def test_plain_answer_path():
    """A text-only response ends the turn with USER + ASSISTANT persisted.

    EN: No tools involved; the final answer is returned and stored.
    中文：不涉及工具；返回并存储最终答复。
    """
    agent, store, tracer, sid = _agent([ModelResponse(text="hello")])
    r = agent.run_turn(sid, "hi")
    assert r.text == "hello" and r.stopped is False
    assert [m.role for m in store.get_messages(sid)] == [Role.USER, Role.ASSISTANT]


def test_single_tool_call_then_answer():
    """One tool call, then a text answer: USER, ASSISTANT(tool), TOOL, ASSISTANT.

    EN: The tool runs and a ``tool_call`` trace event is recorded.
    中文：工具执行，并记录一条 ``tool_call`` 追踪事件。
    """
    script = [ModelResponse(tool_calls=[ToolCall("c1", "echo", {"text": "X"})]), ModelResponse(text="done:X")]
    agent, store, tracer, sid = _agent(script)
    r = agent.run_turn(sid, "use echo")
    assert r.text == "done:X" and r.stopped is False
    roles = [m.role for m in store.get_messages(sid)]
    assert roles == [Role.USER, Role.ASSISTANT, Role.TOOL, Role.ASSISTANT]
    assert any(e.kind == "tool_call" for e in tracer.events)


def test_multi_turn_tool_continuation():
    """Two tool rounds then a final answer; two ``tool_call`` events recorded.

    EN: Confirms the loop keeps feeding tool results back until the model answers.
    中文：确认循环持续回灌工具结果，直到模型给出答复。
    """
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
    """A model that always calls tools is stopped after ``max_tool_iterations``.

    EN: Returns stopped=True/text=None; exactly max_iters tool rounds executed.
    中文：返回 stopped=True/text=None；恰好执行 max_iters 个工具轮。
    """
    script = [ModelResponse(tool_calls=[ToolCall(f"c{i}", "echo", {"text": "x"})]) for i in range(5)]
    agent, store, tracer, sid = _agent(script, max_iters=2)
    r = agent.run_turn(sid, "loop")
    assert r.stopped is True and r.text is None
    # exactly max_iters tool rounds executed before stopping (no further executions)
    assert sum(1 for e in tracer.events if e.kind == "tool_call") == 2


def test_prefetch_recall_is_fenced_message_not_in_frozen_snapshot():
    """Per-turn recall is a fenced message, not part of the frozen snapshot.

    EN —
    Architect fix: ``prefetch`` recall goes into a fenced ``<memory-context>``
    MESSAGE, never the system-prompt snapshot slot; ``self.parts`` is not mutated.

    中文 —
    架构师修复：``prefetch`` 召回进入围栏 ``<memory-context>`` 消息，绝不进入系统提示快照槽位；不改动 ``self.parts``。
    """
    from jobpin_agent.core.system_prompt import SystemPromptParts

    class RecallHooks:
        """A hooks stub whose prefetch returns a recognisable recall string."""

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
