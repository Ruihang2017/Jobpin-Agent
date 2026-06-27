"""Minimal OpenAI adapter (Chat Completions). All OpenAI wire mapping is
isolated here; the rest of the core depends only on ModelProvider. Claude /
DeepSeek / local adapters slot in behind the same ABC at §1.11."""
from __future__ import annotations

import json
from typing import Any

from ..config import CoreConfig
from ..messages import Message, ModelResponse, Role, ToolCall
from ..tools import ToolSpec
from .provider import ModelProvider


def to_openai_messages(messages: list[Message]) -> list[dict]:
    out: list[dict] = []
    for m in messages:
        if m.role is Role.TOOL and m.tool_result is not None:
            out.append({"role": "tool", "tool_call_id": m.tool_result.tool_call_id, "content": m.tool_result.content})
        elif m.role is Role.ASSISTANT and m.tool_calls:
            out.append({
                "role": "assistant",
                "content": m.content or None,
                "tool_calls": [
                    {"id": c.id, "type": "function",
                     "function": {"name": c.name, "arguments": json.dumps(c.arguments)}}
                    for c in m.tool_calls
                ],
            })
        else:
            out.append({"role": m.role.value, "content": m.content})
    return out


def to_openai_tools(tools: list[ToolSpec] | None) -> list[dict] | None:
    if not tools:
        return None
    return [
        {"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.parameters}}
        for t in tools
    ]


def parse_response(resp: Any) -> ModelResponse:
    msg = resp.choices[0].message
    tool_calls = getattr(msg, "tool_calls", None)
    if tool_calls:
        calls = [ToolCall(tc.id, tc.function.name, json.loads(tc.function.arguments or "{}")) for tc in tool_calls]
        return ModelResponse(tool_calls=calls)
    return ModelResponse(text=msg.content or "")


class OpenAIProvider(ModelProvider):
    def __init__(self, config: CoreConfig, client: Any = None) -> None:
        self._config = config
        if client is not None:
            self._client = client
        else:
            from openai import OpenAI  # imported lazily so unit tests need no key

            self._client = OpenAI(api_key=config.openai_api_key)

    def complete(self, messages: list[Message], tools: list[ToolSpec] | None = None) -> ModelResponse:
        kwargs: dict = {"model": self._config.model_id, "messages": to_openai_messages(messages)}
        mapped = to_openai_tools(tools)
        if mapped:
            kwargs["tools"] = mapped
        resp = self._client.chat.completions.create(**kwargs)
        return parse_response(resp)
