"""Provider-agnostic conversation types — the vocabulary of the agent core.

EN —
These dataclasses are the *internal* representation of a conversation. They are
deliberately independent of any LLM provider's wire format: each adapter (e.g.
``OpenAIProvider``) translates between these types and its own API shape. Keeping
one neutral vocabulary is what lets us swap OpenAI / Claude / DeepSeek / a local
model without changing the loop, the tools, or the session store.

中文 —
这些 dataclass 是会话的*内部*表示，刻意独立于任何 LLM 提供商的线格式：每个适配器（如
``OpenAIProvider``）负责在这些类型与其自身 API 形态之间转换。保持单一中立词汇，正是我们能在
OpenAI / Claude / DeepSeek / 本地模型之间切换而无需改动循环、工具或会话存储的原因。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Role(str, Enum):
    """Speaker role of a message.

    EN —
    Mirrors the four conversational roles every chat LLM understands. Subclassing
    ``str`` means a ``Role`` serialises to its plain value (e.g. ``"user"``),
    which keeps JSON persistence and provider mapping trivial.

    中文 —
    对应每个聊天型 LLM 都理解的四种会话角色。继承 ``str`` 使 ``Role`` 序列化为其纯字符串值
    （如 ``"user"``），从而让 JSON 持久化与提供商映射保持简单。
    """

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class ToolCall:
    """A model's request to invoke a tool.

    EN —
    Emitted by a provider when the model decides to call a tool rather than
    answer directly. ``arguments`` is already-parsed JSON (a ``dict``), so the
    rest of the core never re-parses provider strings.

    Attributes:
        id: Provider-assigned id, used to correlate the matching ``ToolResult``.
        name: The tool name, which must exist in the ``ToolRegistry``.
        arguments: Parsed call arguments as a dict.

    中文 —
    当模型决定调用工具而非直接回答时，由提供商产出。``arguments`` 已是解析后的 JSON（``dict``），
    因此内核其余部分无需再解析提供商字符串。

    属性：
        id：提供商分配的 id，用于与对应的 ``ToolResult`` 关联。
        name：工具名，必须存在于 ``ToolRegistry`` 中。
        arguments：解析后的调用参数（dict）。
    """

    id: str
    name: str
    arguments: dict


@dataclass
class ToolResult:
    """The outcome of executing a tool, fed back to the model.

    EN —
    Produced by ``ToolRegistry.execute`` and appended to the conversation so the
    model can continue with the tool's output.

    Attributes:
        tool_call_id: The ``ToolCall.id`` this result answers.
        name: The tool name (kept for readability/audit).
        content: The tool's output, as a string.

    中文 —
    由 ``ToolRegistry.execute`` 产出并追加到会话，使模型可基于工具输出继续。

    属性：
        tool_call_id：本结果所应答的 ``ToolCall.id``。
        name：工具名（保留以便可读性/审计）。
        content：工具输出（字符串）。
    """

    tool_call_id: str
    name: str
    content: str


@dataclass
class Message:
    """One entry in a conversation.

    EN —
    A single message of any role. A plain message carries ``content``; an
    assistant tool-call turn carries ``tool_calls``; a tool turn carries a
    ``tool_result``. This one shape covers all four roles, which keeps the loop
    and the session store uniform.

    Attributes:
        role: Who produced the message.
        content: Text content (may be empty for a tool-call turn).
        tool_calls: Tool calls requested by an assistant turn (else empty).
        tool_result: The result carried by a ``TOOL`` message (else ``None``).

    中文 —
    会话中的单条消息，可为任意角色。纯消息携带 ``content``；助手的工具调用回合携带
    ``tool_calls``；工具回合携带 ``tool_result``。单一形态覆盖四种角色，使循环与会话存储保持统一。

    属性：
        role：消息的产生者。
        content：文本内容（工具调用回合可为空）。
        tool_calls：助手回合请求的工具调用（否则为空）。
        tool_result：``TOOL`` 消息携带的结果（否则为 ``None``）。
    """

    role: Role
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_result: ToolResult | None = None


@dataclass
class ModelResponse:
    """A provider's reply for one model call — either text or tool calls.

    EN —
    Adapters return this from ``ModelProvider.complete``. Exactly one branch is
    meaningful per response: either the model answered (``text``) or it asked to
    call tools (``tool_calls``). The loop uses ``is_tool_call`` to decide.

    Attributes:
        text: The model's text answer, or ``None`` when it called tools.
        tool_calls: Requested tool calls, or empty when it answered directly.

    中文 —
    适配器从 ``ModelProvider.complete`` 返回此对象。每次响应只有一个分支有意义：要么模型作答
    （``text``），要么请求调用工具（``tool_calls``）。循环用 ``is_tool_call`` 判定。

    属性：
        text：模型的文本答复；当其调用工具时为 ``None``。
        tool_calls：请求的工具调用；当其直接作答时为空。
    """

    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)

    @property
    def is_tool_call(self) -> bool:
        """Whether this response is a tool-call (vs a final text answer).

        EN —
        Returns:
            ``True`` if the model requested at least one tool call, else ``False``.

        中文 —
        返回：
            若模型至少请求了一个工具调用则为 ``True``，否则为 ``False``。
        """
        return bool(self.tool_calls)
