"""End-to-end §1.1 demo — plain turn, tool-call turn, and delegation.

EN —
Wires up an ``Agent`` with the ``echo`` tool, a SQLite session store and a tracer,
then exercises all three behaviours. Uses the offline ``FakeProvider`` by default
so it is deterministic and needs no API key; pass a ``provider_factory`` to run it
against a real backend (e.g. OpenAI). Returns a small dict so it can be asserted
in tests as well as printed when run directly.

中文 —
将一个 ``Agent`` 与 ``echo`` 工具、SQLite 会话存储和追踪器连接起来，然后演练三种行为。默认使用离线
``FakeProvider``，因此确定性且无需 API 密钥；传入 ``provider_factory`` 可对接真实后端（如 OpenAI）。返回一个小
dict，既可在测试中断言，也可在直接运行时打印。
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow `python agent/examples/demo_turn.py` without setting PYTHONPATH.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpin_agent.core.agent_loop import Agent
from jobpin_agent.core.delegation import delegate
from jobpin_agent.core.messages import ModelResponse, ToolCall
from jobpin_agent.core.model.fake_provider import FakeProvider
from jobpin_agent.core.session_store import SessionStore
from jobpin_agent.core.tools import ToolRegistry, echo_tool
from jobpin_agent.core.tracing import Tracer


def run_demo(provider_factory=None) -> dict:
    """Run the plain / tool-call / delegation demo and return a result summary.

    EN —
    Args:
        provider_factory: Optional zero-arg callable returning a ``ModelProvider``
            for each agent. When ``None`` (default), a scripted ``FakeProvider`` is
            used so the demo is offline and deterministic.
    Returns:
        A dict ``{"plain", "tool", "delegation", "trace_events"}`` summarising the
        three turns and how many trace events were recorded.

    中文 —
    参数：
        provider_factory：可选的零参可调用对象，为每个 agent 返回一个 ``ModelProvider``。为 ``None``（默认）时
            使用脚本化 ``FakeProvider``，使演示离线且确定性。
    返回：
        一个 dict ``{"plain", "tool", "delegation", "trace_events"}``，概述三个回合及记录的追踪事件数。
    """
    reg = ToolRegistry()
    reg.register(echo_tool())
    store = SessionStore()
    tracer = Tracer()

    def make(script):
        return provider_factory() if provider_factory else FakeProvider(script)

    # plain
    a1 = Agent(make([ModelResponse(text="hello")]), reg, store, tracer=tracer)
    s1 = store.create_session("plain")
    plain = a1.run_turn(s1, "hi").text

    # tool-call
    a2 = Agent(
        make([ModelResponse(tool_calls=[ToolCall("c1", "echo", {"text": "X"})]), ModelResponse(text="done:X")]),
        reg, store, tracer=tracer,
    )
    s2 = store.create_session("tool")
    tool = a2.run_turn(s2, "use echo").text

    # delegation
    parent = Agent(make([ModelResponse(text="parent")]), reg, store, tracer=tracer)
    store.create_session("parent")
    deleg = delegate(
        parent, "do subtask",
        child_provider=make([ModelResponse(text="child-done")]),
        child_session_id="child", parent_session_id="parent",
    ).text

    return {"plain": plain, "tool": tool, "delegation": deleg, "trace_events": len(tracer.events)}


if __name__ == "__main__":  # pragma: no cover
    print(run_demo())
