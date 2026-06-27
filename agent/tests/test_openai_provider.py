import os
import pytest
from jobpin_agent.core.config import CoreConfig
from jobpin_agent.core.messages import Message, Role, ToolCall, ToolResult
from jobpin_agent.core.tools import echo_tool
from jobpin_agent.core.model.openai_provider import (
    OpenAIProvider, to_openai_messages, to_openai_tools, parse_response,
)


def test_to_openai_messages_maps_roles_and_tool_calls():
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
    tools = to_openai_tools([echo_tool()])
    assert tools[0]["type"] == "function" and tools[0]["function"]["name"] == "echo"


class _Fn:
    def __init__(self, name, args):
        self.name = name
        self.arguments = args


class _TC:
    def __init__(self, id, name, args):
        self.id = id
        self.function = _Fn(name, args)


class _Msg:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


class _Choice:
    def __init__(self, msg):
        self.message = msg


class _Resp:
    def __init__(self, choice):
        self.choices = [choice]


def test_parse_response_text_and_tool_calls():
    text = parse_response(_Resp(_Choice(_Msg(content="hello"))))
    assert text.text == "hello" and text.is_tool_call is False
    tc = parse_response(_Resp(_Choice(_Msg(tool_calls=[_TC("c1", "echo", '{"text": "x"}')]))))
    assert tc.is_tool_call and tc.tool_calls[0].name == "echo" and tc.tool_calls[0].arguments == {"text": "x"}


@pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="no OPENAI_API_KEY; opt-in integration test")
def test_openai_integration_real_turn():
    provider = OpenAIProvider(CoreConfig.from_env())
    resp = provider.complete([Message(Role.USER, "Reply with the single word: pong")], tools=None)
    assert resp.text and "pong" in resp.text.lower()
