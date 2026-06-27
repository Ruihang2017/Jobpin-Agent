"""``OpenAIProvider`` — the first real model adapter (OpenAI Chat Completions).

EN —
This is the ONLY place that knows OpenAI's wire format. The module-level mapping
helpers convert between the internal types and OpenAI's request/response shapes;
the rest of the core never sees an OpenAI payload. OpenAI is the dev/pilot default
(PRD §11.3); Claude / DeepSeek / local adapters will live alongside this behind
the same ``ModelProvider`` ABC. The ``openai`` package is imported lazily so unit
tests (which inject a fake client or call the mappers directly) need no key.

中文 —
这是唯一了解 OpenAI 线格式的地方。模块级映射辅助函数在内部类型与 OpenAI 请求/响应形态之间转换；内核其余部分
绝不接触 OpenAI 负载。OpenAI 为开发/试点默认（PRD §11.3）；Claude / DeepSeek / 本地适配器将在同一
``ModelProvider`` 抽象基类下与之并存。``openai`` 包延迟导入，使单元测试（注入伪客户端或直接调用映射函数）无需密钥。
"""
from __future__ import annotations

import json
from typing import Any

from ..config import CoreConfig
from ..messages import Message, ModelResponse, Role, ToolCall
from ..tools import ToolSpec
from .provider import ModelProvider


def to_openai_messages(messages: list[Message]) -> list[dict]:
    """Map internal messages to OpenAI Chat Completions message dicts.

    EN —
    Handles the three special shapes: a tool result becomes a ``role:"tool"`` dict
    keyed by ``tool_call_id``; an assistant tool-call turn carries an OpenAI
    ``tool_calls`` array (with JSON-stringified arguments); everything else is a
    plain ``{role, content}``.
    Args:
        messages: Internal messages (system prompt + history).
    Returns:
        A list of OpenAI-shaped message dicts.

    中文 —
    处理三种特殊形态：工具结果变为以 ``tool_call_id`` 为键的 ``role:"tool"`` dict；助手的工具调用回合携带 OpenAI
    ``tool_calls`` 数组（参数 JSON 字符串化）；其余为普通 ``{role, content}``。
    参数：
        messages：内部消息（系统提示 + 历史）。
    返回：
        OpenAI 形态的消息 dict 列表。
    """
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
    """Map internal tool specs to OpenAI's ``tools`` parameter.

    EN —
    Args:
        tools: Tools to advertise, or ``None``/empty.
    Returns:
        OpenAI function-tool dicts, or ``None`` when there are no tools (so the
        caller can omit the ``tools`` kwarg entirely).

    中文 —
    参数：
        tools：要告知的工具，或 ``None``/空。
    返回：
        OpenAI 函数工具 dict；无工具时为 ``None``（便于调用方完全省略 ``tools`` 参数）。
    """
    if not tools:
        return None
    return [
        {"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.parameters}}
        for t in tools
    ]


def _usage_dict(resp: Any) -> dict | None:
    """Extract a token-usage dict from an OpenAI completion, if present.

    EN —
    Args:
        resp: An OpenAI completion (or fake). Reads its ``usage`` attribute.
    Returns:
        ``{"prompt_tokens", "completion_tokens", "total_tokens"}`` or ``None`` when
        the response carries no usage info.

    中文 —
    参数：
        resp：OpenAI completion（或伪对象）。读取其 ``usage`` 属性。
    返回：
        ``{"prompt_tokens", "completion_tokens", "total_tokens"}``；当响应不含用量信息时为 ``None``。
    """
    usage = getattr(resp, "usage", None)
    if usage is None:
        return None
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
    }


def parse_response(resp: Any) -> ModelResponse:
    """Convert an OpenAI completion object into a ``ModelResponse``.

    EN —
    Reads the first choice: if it has ``tool_calls``, returns those (parsing each
    function's JSON arguments back into a dict); otherwise returns the text. Token
    usage is attached when the response reports it.
    Args:
        resp: An OpenAI completion (or any object with the same shape — tests pass
            lightweight fakes).
    Returns:
        A ``ModelResponse`` (text or tool calls), with ``usage`` populated if available.

    中文 —
    读取第一个 choice：若含 ``tool_calls`` 则返回之（将每个 function 的 JSON 参数解析回 dict）；否则返回文本。
    若响应报告了 token 用量则一并附上。
    参数：
        resp：OpenAI completion（或任何同形态对象——测试传入轻量伪对象）。
    返回：
        一个 ``ModelResponse``（文本或工具调用），若可用则填充 ``usage``。
    """
    msg = resp.choices[0].message
    usage = _usage_dict(resp)
    tool_calls = getattr(msg, "tool_calls", None)
    if tool_calls:
        calls = [ToolCall(tc.id, tc.function.name, json.loads(tc.function.arguments or "{}")) for tc in tool_calls]
        return ModelResponse(tool_calls=calls, usage=usage)
    return ModelResponse(text=msg.content or "", usage=usage)


class OpenAIProvider(ModelProvider):
    """A ``ModelProvider`` backed by OpenAI Chat Completions.

    EN —
    Holds the model id (from config) and an OpenAI client. The client can be
    injected (tests pass a fake); otherwise it is constructed lazily from the
    config's API key.

    中文 —
    持有模型 id（来自配置）与一个 OpenAI 客户端。客户端可注入（测试传入伪对象）；否则按配置的 API 密钥延迟构造。
    """

    def __init__(self, config: CoreConfig, client: Any = None) -> None:
        """Create the provider.

        EN —
        Args:
            config: Core config (provides ``model_id`` and ``openai_api_key``).
            client: An optional pre-built OpenAI client; if ``None``, a real
                ``openai.OpenAI`` is created lazily (so tests need no key).

        中文 —
        参数：
            config：核心配置（提供 ``model_id`` 与 ``openai_api_key``）。
            client：可选的预构建 OpenAI 客户端；为 ``None`` 时延迟创建真实 ``openai.OpenAI``
                （故测试无需密钥）。
        """
        self._config = config
        if client is not None:
            self._client = client
        else:
            from openai import OpenAI  # imported lazily so unit tests need no key

            self._client = OpenAI(api_key=config.openai_api_key)

    def complete(self, messages: list[Message], tools: list[ToolSpec] | None = None) -> ModelResponse:
        """Call OpenAI once and return the mapped response.

        EN —
        Maps messages/tools to OpenAI shapes, omits the ``tools`` kwarg when there
        are none, calls ``chat.completions.create``, and parses the result.
        Args:
            messages: The conversation to send.
            tools: Tools the model may call, or ``None``.
        Returns:
            A ``ModelResponse`` (text or tool calls).

        中文 —
        将消息/工具映射为 OpenAI 形态，无工具时省略 ``tools`` 参数，调用 ``chat.completions.create`` 并解析结果。
        参数：
            messages：要发送的会话。
            tools：模型可调用的工具，或 ``None``。
        返回：
            一个 ``ModelResponse``（文本或工具调用）。
        """
        kwargs: dict = {"model": self._config.model_id, "messages": to_openai_messages(messages)}
        mapped = to_openai_tools(tools)
        if mapped:
            kwargs["tools"] = mapped
        resp = self._client.chat.completions.create(**kwargs)
        return parse_response(resp)
