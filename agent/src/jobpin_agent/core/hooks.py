"""The memory seam. §1.1 ships only NoOpHooks; §1.2-1.6 provide real ones
without touching the loop. Hook set mirrors Hermes MemoryProvider lifecycle."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from .messages import Message


@runtime_checkable
class MemoryHooks(Protocol):
    def prefetch(self, query: str, session_id: str) -> str: ...
    def after_turn(self, session_id: str, messages: list[Message]) -> None: ...
    def on_delegation(self, task: str, result: str, child_session_id: str) -> None: ...
    def on_session_switch(self, new_session_id: str, parent_session_id: str | None, reset: bool, rewound: bool) -> None: ...
    def on_pre_compress(self, messages: list[Message]) -> str: ...


class NoOpHooks:
    def prefetch(self, query: str, session_id: str) -> str:
        return ""

    def after_turn(self, session_id: str, messages: list[Message]) -> None:
        return None

    def on_delegation(self, task: str, result: str, child_session_id: str) -> None:
        return None

    def on_session_switch(self, new_session_id: str, parent_session_id: str | None, reset: bool, rewound: bool) -> None:
        return None

    def on_pre_compress(self, messages: list[Message]) -> str:
        return ""
