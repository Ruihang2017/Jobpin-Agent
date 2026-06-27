"""Tests for the offline scripted ``FakeProvider``.

EN —
Confirms the test double behaves predictably: it returns scripted responses in
order, records calls, and fails loudly when over-used.
中文 —
确认该测试替身行为可预期：按顺序返回脚本响应、记录调用，并在被过度使用时显式失败。
"""
from jobpin_agent.core.messages import Message, Role, ModelResponse, ToolCall
from jobpin_agent.core.model.fake_provider import FakeProvider


def test_fake_provider_returns_script_in_order_and_records_calls():
    """Responses come back in script order, and each call is recorded.

    EN: Two scripted responses are returned in sequence; ``calls`` captures the
    messages of each ``complete`` invocation.
    中文：两个脚本响应按序返回；``calls`` 记录每次 ``complete`` 调用的消息。
    """
    p = FakeProvider([ModelResponse(text="hi"), ModelResponse(tool_calls=[ToolCall("c1", "echo", {"text": "x"})])])
    r1 = p.complete([Message(Role.USER, "hello")], tools=None)
    r2 = p.complete([Message(Role.USER, "again")], tools=None)
    assert r1.text == "hi" and r1.is_tool_call is False
    assert r2.is_tool_call is True and r2.tool_calls[0].name == "echo"
    assert len(p.calls) == 2 and p.calls[0][0].content == "hello"


def test_fake_provider_raises_when_exhausted():
    """Calling past the end of the script raises a clear ``AssertionError``.

    EN: Protects tests from silently asking for more model turns than scripted.
    中文：防止测试在无声中请求多于脚本编排的模型回合。
    """
    p = FakeProvider([])
    try:
        p.complete([], None)
        assert False, "expected AssertionError"
    except AssertionError as e:
        assert "exhausted" in str(e)
