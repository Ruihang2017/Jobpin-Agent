import pytest
from jobpin_agent.core.messages import ToolCall
from jobpin_agent.core.tools import ToolRegistry, echo_tool


def test_registry_executes_registered_tool():
    reg = ToolRegistry()
    reg.register(echo_tool())
    result = reg.execute(ToolCall("c1", "echo", {"text": "hello"}))
    assert result.content == "hello" and result.tool_call_id == "c1"


def test_registry_unknown_tool_raises():
    reg = ToolRegistry()
    with pytest.raises(KeyError):
        reg.get("nope")
