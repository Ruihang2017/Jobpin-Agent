"""Tests for the OpenAI adapter (wire mapping + kwargs + opt-in integration).

EN —
Exercises the message/tool mapping and response parsing with lightweight fakes
(no key/network), verifies ``tools`` is omitted when there are none, and includes
a real OpenAI integration test that runs only when ``OPENAI_API_KEY`` is set.
中文 —
用轻量伪对象（无密钥/网络）演练消息/工具映射与响应解析，验证无工具时省略 ``tools``，并含一个仅在设置
``OPENAI_API_KEY`` 时运行的真实 OpenAI 集成测试。
"""
import os
import pytest
from jobpin_agent.core.config import CoreConfig
from jobpin_agent.core.messages import Message, Role, ToolCall, ToolResult
from jobpin_agent.core.tools import echo_tool
from jobpin_agent.core.model.openai_provider import (
    OpenAIProvider, to_openai_messages, to_openai_tools, parse_response,
)


def test_to_openai_messages_maps_roles_and_tool_calls():
    """Internal messages map to OpenAI dicts, incl. tool-call and tool-result shapes.

    EN: system/user pass through; assistant tool-calls become a tool_calls array;
    a tool result becomes a role:"tool" dict keyed by tool_call_id.
    中文：system/user 透传；助手工具调用变为 tool_calls 数组；工具结果变为以 tool_call_id 为键的 role:"tool" dict。
    """
    msgs = [
        Message(Role.SYSTEM, "sys"),
        Message(Role.USER, "hi"),
        Message(Role.ASSISTANT, tool_calls=[ToolCall("c1", "echo", {"text": "x"})]),
        Message(Role.TOOL, tool_result=ToolResult("c1", "echo", "x")),
    ]
    out = to_openai_messages(msgs)
    assert out[0] == {"role": "system", "content": "sys"}
    assert out[2]["tool_calls"][0]["function"]["name"] == "echo"
    assert out[3] == {"role": "tool", "tool_call_id": "c1", "content": "x"}


def test_to_openai_tools_shape():
    """Tool specs map to OpenAI function-tool dicts.

    EN: Each tool becomes {type:"function", function:{name,...}}.
    中文：每个工具变为 {type:"function", function:{name,...}}。
    """
    tools = to_openai_tools([echo_tool()])
    assert tools[0]["type"] == "function" and tools[0]["function"]["name"] == "echo"


class _Fn:
    """Fake OpenAI ``function`` object (name + JSON-string arguments)."""

    def __init__(self, name, args):
        self.name = name
        self.arguments = args


class _TC:
    """Fake OpenAI ``tool_call`` object."""

    def __init__(self, id, name, args):
        self.id = id
        self.function = _Fn(name, args)


class _Msg:
    """Fake OpenAI ``message`` object (content and/or tool_calls)."""

    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


class _Choice:
    """Fake OpenAI ``choice`` wrapping a message."""

    def __init__(self, msg):
        self.message = msg


class _Resp:
    """Fake OpenAI completion wrapping a single choice."""

    def __init__(self, choice):
        self.choices = [choice]


def test_parse_response_text_and_tool_calls():
    """``parse_response`` returns text for a text msg and parsed tool calls otherwise.

    EN: Tool-call arguments are JSON-parsed back into a dict.
    中文：工具调用参数被 JSON 解析回 dict。
    """
    text = parse_response(_Resp(_Choice(_Msg(content="hello"))))
    assert text.text == "hello" and text.is_tool_call is False
    tc = parse_response(_Resp(_Choice(_Msg(tool_calls=[_TC("c1", "echo", '{"text": "x"}')]))))
    assert tc.is_tool_call and tc.tool_calls[0].name == "echo" and tc.tool_calls[0].arguments == {"text": "x"}


def test_complete_omits_tools_when_none_and_includes_when_present():
    """``complete`` omits the ``tools`` kwarg when there are no tools, includes it otherwise.

    EN: Uses a capturing fake client to inspect the kwargs sent to OpenAI.
    中文：使用捕获式伪客户端检查发往 OpenAI 的 kwargs。
    """
    class _Comp:
        def __init__(self, sink):
            self._sink = sink

        def create(self, **kwargs):
            self._sink.append(kwargs)
            return _Resp(_Choice(_Msg(content="ok")))

    class _Chat:
        def __init__(self, sink):
            self.completions = _Comp(sink)

    class _Client:
        def __init__(self, sink):
            self.chat = _Chat(sink)

    sink: list = []
    provider = OpenAIProvider(CoreConfig(model_id="m"), client=_Client(sink))
    provider.complete([Message(Role.USER, "hi")], tools=None)
    assert "tools" not in sink[0]
    provider.complete([Message(Role.USER, "hi")], tools=[echo_tool()])
    assert sink[1]["tools"][0]["function"]["name"] == "echo"


@pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="no OPENAI_API_KEY; opt-in integration test")
def test_openai_integration_real_turn():
    """Real OpenAI round-trip — runs only when ``OPENAI_API_KEY`` is set.

    EN: Sends a trivial prompt and checks the model echoes the expected word.
    中文：发送一个简单提示并检查模型回显预期词。
    """
    provider = OpenAIProvider(CoreConfig.from_env())
    resp = provider.complete([Message(Role.USER, "Reply with the single word: pong")], tools=None)
    assert resp.text and "pong" in resp.text.lower()
