"""Provider-agnostic conversation types. No model wire formats here."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class ToolResult:
    tool_call_id: str
    name: str
    content: str


@dataclass
class Message:
    role: Role
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_result: ToolResult | None = None


@dataclass
class ModelResponse:
    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)

    @property
    def is_tool_call(self) -> bool:
        return bool(self.tool_calls)
