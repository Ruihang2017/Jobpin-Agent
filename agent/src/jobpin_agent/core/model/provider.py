"""Provider-agnostic model abstraction. Design borrowed from Hermes's
multi-provider layer, rewritten minimal and ownable (PRD §2.7)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from ..messages import Message, ModelResponse

if TYPE_CHECKING:
    from ..tools import ToolSpec


class ModelProvider(ABC):
    @abstractmethod
    def complete(self, messages: list[Message], tools: "list[ToolSpec] | None" = None) -> ModelResponse:
        """Return either a text answer or tool calls for the given messages."""
        raise NotImplementedError
