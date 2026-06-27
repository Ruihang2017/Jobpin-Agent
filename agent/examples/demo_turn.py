"""Runnable §1.1 demo: plain turn, tool-call turn, delegation. Uses the
FakeProvider by default (offline/deterministic); pass a provider_factory to
run against OpenAI."""
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
