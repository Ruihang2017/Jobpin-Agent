"""Deterministic, offline provider for tests."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..messages import Message, ModelResponse
from .provider import ModelProvider

if TYPE_CHECKING:
    from ..tools import ToolSpec


class FakeProvider(ModelProvider):
    def __init__(self, script: list[ModelResponse]) -> None:
        self._script = list(script)
        self.calls: list[list[Message]] = []

    def complete(self, messages: list[Message], tools: "list[ToolSpec] | None" = None) -> ModelResponse:
        self.calls.append(list(messages))
        if not self._script:
            raise AssertionError("FakeProvider script exhausted")
        return self._script.pop(0)
