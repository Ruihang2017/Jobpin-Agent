from jobpin_agent.core.messages import Message, Role, ModelResponse, ToolCall
from jobpin_agent.core.model.fake_provider import FakeProvider


def test_fake_provider_returns_script_in_order_and_records_calls():
    p = FakeProvider([ModelResponse(text="hi"), ModelResponse(tool_calls=[ToolCall("c1", "echo", {"text": "x"})])])
    r1 = p.complete([Message(Role.USER, "hello")], tools=None)
    r2 = p.complete([Message(Role.USER, "again")], tools=None)
    assert r1.text == "hi" and r1.is_tool_call is False
    assert r2.is_tool_call is True and r2.tool_calls[0].name == "echo"
    assert len(p.calls) == 2 and p.calls[0][0].content == "hello"


def test_fake_provider_raises_when_exhausted():
    p = FakeProvider([])
    try:
        p.complete([], None)
        assert False, "expected AssertionError"
    except AssertionError as e:
        assert "exhausted" in str(e)
