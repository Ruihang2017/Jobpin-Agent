"""Tests for the tool registry.

EN —
Confirms tools can be registered and executed, and that unknown tools fail loudly.
中文 —
确认工具可注册与执行，且未知工具会显式失败。
"""
import pytest
from jobpin_agent.core.messages import ToolCall
from jobpin_agent.core.tools import ToolRegistry, echo_tool


def test_registry_executes_registered_tool():
    """A registered tool runs and returns a correlated ``ToolResult``.

    EN: ``echo`` returns its text; the result keeps the originating call id.
    中文：``echo`` 返回其文本；结果保留源调用 id。
    """
    reg = ToolRegistry()
    reg.register(echo_tool())
    result = reg.execute(ToolCall("c1", "echo", {"text": "hello"}))
    assert result.content == "hello" and result.tool_call_id == "c1"


def test_registry_unknown_tool_raises():
    """Looking up an unregistered tool raises ``KeyError``.

    EN: Guards against silently ignoring an unknown tool name.
    中文：防止无声忽略未知工具名。
    """
    reg = ToolRegistry()
    with pytest.raises(KeyError):
        reg.get("nope")
