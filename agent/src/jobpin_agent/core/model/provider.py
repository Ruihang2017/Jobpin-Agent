"""The ``ModelProvider`` abstraction — the seam between the loop and any LLM.

EN —
Every model backend (OpenAI now; Claude / DeepSeek / local at §1.11) implements
this one method. The agent loop depends only on this ABC and the internal message
types, so adding or swapping a backend never touches the loop. Design borrowed
from Hermes's provider-agnostic model layer (PRD §2.7, §11.3).

中文 —
每个模型后端（现为 OpenAI；§1.11 引入 Claude / DeepSeek / 本地）都实现这一个方法。agent 循环只依赖此抽象基类
与内部消息类型，故新增或替换后端绝不触及循环。设计借鉴自 Hermes 的 provider 无关模型层（PRD §2.7、§11.3）。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from ..messages import Message, ModelResponse

if TYPE_CHECKING:
    from ..tools import ToolSpec


class ModelProvider(ABC):
    """Abstract base class for LLM backends.

    EN —
    Subclasses translate between the internal types and a vendor API. The contract
    is intentionally tiny: one ``complete`` call per model turn.

    中文 —
    子类负责在内部类型与厂商 API 之间转换。契约刻意精简：每个模型回合一次 ``complete`` 调用。
    """

    @abstractmethod
    def complete(self, messages: list[Message], tools: "list[ToolSpec] | None" = None) -> ModelResponse:
        """Produce one model response for the given conversation.

        EN —
        Args:
            messages: The full conversation so far (system prompt + history).
            tools: Tools the model may call this turn, or ``None`` for none.
        Returns:
            A ``ModelResponse`` — either a text answer or one/more tool calls.

        中文 —
        参数：
            messages：迄今为止的完整会话（系统提示 + 历史）。
            tools：本回合模型可调用的工具；无则为 ``None``。
        返回：
            一个 ``ModelResponse``——文本答复，或一个/多个工具调用。
        """
        raise NotImplementedError
