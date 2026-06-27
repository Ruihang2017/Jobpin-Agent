"""Tool registry with structured (JSON-schema) tool specs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .messages import ToolCall, ToolResult


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict  # JSON schema
    handler: Callable[[dict], str]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec:
        if name not in self._tools:
            raise KeyError(f"unknown tool: {name}")
        return self._tools[name]

    def specs(self) -> list[ToolSpec]:
        return list(self._tools.values())

    def execute(self, call: ToolCall) -> ToolResult:
        spec = self.get(call.name)
        content = spec.handler(call.arguments)
        return ToolResult(tool_call_id=call.id, name=call.name, content=content)


def echo_tool() -> ToolSpec:
    return ToolSpec(
        name="echo",
        description="Echo back the provided text.",
        parameters={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
        handler=lambda args: str(args.get("text", "")),
    )
