"""Sub-agent delegation. Invariant (Key Invariant #3): children run with
skip_memory=True (NoOpHooks) and never persist sensitive memory; the parent
observes the result via on_delegation and adjudicates writes (no-op until
memory exists). Design borrowed from Hermes on_delegation."""
from __future__ import annotations

from dataclasses import dataclass

from .agent_loop import Agent
from .hooks import NoOpHooks
from .model.provider import ModelProvider


@dataclass
class DelegationResult:
    text: str | None
    child_session_id: str


def delegate(
    parent: Agent,
    task: str,
    child_provider: ModelProvider,
    child_session_id: str | None = None,
    parent_session_id: str | None = None,
) -> DelegationResult:
    # Child shares the parent's tools + session DB + prompt context (org / compliance /
    # role), but runs skip_memory (NoOpHooks). parent_session_id records lineage for
    # the §1.7 / audit causal chain.
    child = Agent(
        provider=child_provider,
        tools=parent.tools,
        session_store=parent.store,
        tracer=parent.tracer,
        hooks=NoOpHooks(),  # skip_memory: child writes no sensitive memory
        parts=parent.parts,
        max_tool_iterations=parent.max_tool_iterations,
    )
    sid = parent.store.create_session(child_session_id, parent_id=parent_session_id)
    parent.tracer.event("delegation", task=task, child_session_id=sid)
    result = child.run_turn(sid, task)
    parent.hooks.on_delegation(task, result.text or "", sid)
    return DelegationResult(text=result.text, child_session_id=sid)
