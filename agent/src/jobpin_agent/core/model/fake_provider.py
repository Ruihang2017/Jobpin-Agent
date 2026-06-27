"""``FakeProvider`` — a scripted, offline model backend for tests.

EN —
Returns pre-written ``ModelResponse`` objects in order, and records the messages
it was called with. This lets the loop, delegation, and demo be tested
deterministically with no network, no API key, and no cost — the model's
behaviour is whatever the test scripts.

中文 —
按顺序返回预先写好的 ``ModelResponse`` 对象，并记录每次调用收到的消息。这使循环、委派与演示可在无网络、无 API
密钥、无费用的情况下确定性地测试——模型行为即测试所编排的脚本。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..messages import Message, ModelResponse
from .provider import ModelProvider

if TYPE_CHECKING:
    from ..tools import ToolSpec


class FakeProvider(ModelProvider):
    """A deterministic provider driven by a fixed script.

    EN —
    Attributes:
        calls: Records each call's message list, so tests can assert what the loop
            sent to the model (e.g. that recall was fenced into the messages).

    中文 —
    属性：
        calls：记录每次调用的消息列表，使测试可断言循环发给模型的内容（如召回是否被围栏注入消息）。
    """

    def __init__(self, script: list[ModelResponse]) -> None:
        """Create a fake provider.

        EN —
        Args:
            script: The responses to return, one per ``complete`` call, in order.

        中文 —
        参数：
            script：要返回的响应，按顺序每次 ``complete`` 调用返回一个。
        """
        self._script = list(script)
        self.calls: list[list[Message]] = []

    def complete(self, messages: list[Message], tools: "list[ToolSpec] | None" = None) -> ModelResponse:
        """Return the next scripted response and record the call.

        EN —
        Args:
            messages: The conversation the loop sent (recorded into ``calls``).
            tools: Ignored (kept for interface parity with real providers).
        Returns:
            The next ``ModelResponse`` from the script.
        Raises:
            AssertionError: If the script is exhausted (a test asked for more
                model turns than it scripted).

        中文 —
        参数：
            messages：循环发来的会话（记录到 ``calls``）。
            tools：忽略（保留以与真实 provider 接口一致）。
        返回：
            脚本中的下一个 ``ModelResponse``。
        抛出：
            AssertionError：若脚本耗尽（测试请求的模型回合多于其编排的）。
        """
        self.calls.append(list(messages))
        if not self._script:
            raise AssertionError("FakeProvider script exhausted")
        return self._script.pop(0)
