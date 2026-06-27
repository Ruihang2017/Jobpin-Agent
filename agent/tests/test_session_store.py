"""Tests for the SQLite session store.

EN —
Confirms lossless round-trip of messages (incl. tool calls/results) and that
branch/reset behave correctly and fire ``on_session_switch``.
中文 —
确认消息（含工具调用/结果）的无损往返，以及 branch/reset 行为正确并触发 ``on_session_switch``。
"""
from jobpin_agent.core.messages import Message, Role, ToolCall, ToolResult
from jobpin_agent.core.session_store import SessionStore


class RecordingHooks:
    """A ``MemoryHooks`` stub that records ``on_session_switch`` calls.

    EN: Lets tests assert which switches fired with what flags.
    中文：使测试可断言触发了哪些切换及其标志。
    """

    def __init__(self):
        self.switches = []

    def prefetch(self, q, session_id):
        return ""

    def after_turn(self, s, m):
        return None

    def on_delegation(self, t, r, c):
        return None

    def on_session_switch(self, new, parent, reset, rewound):
        self.switches.append((new, parent, reset, rewound))

    def on_pre_compress(self, m):
        return ""


def test_roundtrip_preserves_messages_with_tool_calls():
    """Messages survive a store/read round-trip, including tool call args.

    EN: Roles, the tool name, the parsed arguments dict, and the tool result all
    come back intact after JSON serialisation.
    中文：经 JSON 序列化后，角色、工具名、解析后的参数 dict 与工具结果均完整返回。
    """
    s = SessionStore()
    sid = s.create_session("s1")
    s.append_message(sid, Message(Role.USER, "hi"))
    s.append_message(sid, Message(Role.ASSISTANT, tool_calls=[ToolCall("c1", "echo", {"text": "x"})]))
    s.append_message(sid, Message(Role.TOOL, tool_result=ToolResult("c1", "echo", "x")))
    msgs = s.get_messages(sid)
    assert [m.role for m in msgs] == [Role.USER, Role.ASSISTANT, Role.TOOL]
    assert msgs[1].tool_calls[0].name == "echo"
    assert msgs[1].tool_calls[0].arguments == {"text": "x"}
    assert msgs[2].tool_result.content == "x"


def test_branch_forks_history_and_fires_switch():
    """Branch copies history into a new session and fires a non-reset switch.

    EN: The new session has the forked history; on_session_switch reset flag is False.
    中文：新会话拥有分叉历史；on_session_switch 的 reset 标志为 False。
    """
    h = RecordingHooks()
    s = SessionStore(hooks=h)
    sid = s.create_session("s1")
    s.append_message(sid, Message(Role.USER, "hi"))
    new = s.branch(sid, "s2")
    assert [m.content for m in s.get_messages(new)] == ["hi"]
    assert h.switches[0][0] == "s2" and h.switches[0][2] is False


def test_reset_clears_and_fires_switch():
    """Reset empties a session's messages and fires a reset switch.

    EN: get_messages becomes empty; the last on_session_switch reset flag is True.
    中文：get_messages 变空；最后一次 on_session_switch 的 reset 标志为 True。
    """
    h = RecordingHooks()
    s = SessionStore(hooks=h)
    sid = s.create_session("s1")
    s.append_message(sid, Message(Role.USER, "hi"))
    s.reset(sid)
    assert s.get_messages(sid) == []
    assert h.switches[-1][2] is True
