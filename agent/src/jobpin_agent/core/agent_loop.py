"""Lean synchronous conversation loop. Design borrowed from Hermes
conversation_loop.run_conversation, rewritten minimal and ownable (PRD §2.7).
Memory recall/persist are routed through the no-op MemoryHooks seam."""
from __future__ import annotations

from dataclasses import dataclass, field

from .hooks import MemoryHooks, NoOpHooks
from .messages import Message, Role
from .model.provider import ModelProvider
from .session_store import SessionStore
from .system_prompt import SystemPromptParts, build_system_prompt
from .tools import ToolRegistry
from .tracing import Tracer


@dataclass
class TurnResult:
    text: str | None
    stopped: bool
    messages: list[Message] = field(default_factory=list)


class Agent:
    def __init__(
        self,
        provider: ModelProvider,
        tools: ToolRegistry,
        session_store: SessionStore,
        tracer: Tracer | None = None,
        hooks: MemoryHooks | None = None,
        parts: SystemPromptParts | None = None,
        max_tool_iterations: int = 8,
    ) -> None:
        self.provider = provider
        self.tools = tools
        self.store = session_store
        self.tracer = tracer or Tracer()
        self.hooks = hooks or NoOpHooks()
        self.parts = parts or SystemPromptParts()
        self.max_tool_iterations = max_tool_iterations

    def _compose(self, history: list[Message]) -> list[Message]:
        parts = SystemPromptParts(
            org_policy=self.parts.org_policy,
            compliance=self.parts.compliance,
            role_permissions=self.parts.role_permissions,
            memory_snapshot=self.parts.memory_snapshot,
            provider_block=self.parts.provider_block,
            tools=self.tools.specs(),
        )
        system = Message(Role.SYSTEM, content=build_system_prompt(parts))
        return [system, *history]

    def run_turn(self, session_id: str, user_input: str) -> TurnResult:
        self.tracer.event("turn_start", session_id=session_id)
        # memory recall seam (no-op in §1.1); fed into the snapshot slot
        self.parts.memory_snapshot = self.hooks.prefetch(user_input) or self.parts.memory_snapshot
        self.store.append_message(session_id, Message(Role.USER, content=user_input))
        iterations = 0
        while True:
            history = self.store.get_messages(session_id)
            self.tracer.event("model_call", iteration=iterations)
            response = self.provider.complete(self._compose(history), self.tools.specs())
            if response.is_tool_call:
                if iterations >= self.max_tool_iterations:
                    self.tracer.event("turn_end", stopped=True)
                    return TurnResult(text=None, stopped=True, messages=self.store.get_messages(session_id))
                self.store.append_message(session_id, Message(Role.ASSISTANT, tool_calls=response.tool_calls))
                for call in response.tool_calls:
                    self.tracer.event("tool_call", name=call.name)
                    result = self.tools.execute(call)
                    self.store.append_message(session_id, Message(Role.TOOL, tool_result=result))
                iterations += 1
                continue
            self.store.append_message(session_id, Message(Role.ASSISTANT, content=response.text or ""))
            final = self.store.get_messages(session_id)
            self.hooks.after_turn(session_id, final)
            self.tracer.event("turn_end", stopped=False)
            return TurnResult(text=response.text, stopped=False, messages=final)
