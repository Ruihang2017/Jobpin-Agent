from jobpin_agent.core.messages import Message, Role, ToolCall, ToolResult
from jobpin_agent.core.session_store import SessionStore


class RecordingHooks:
    def __init__(self):
        self.switches = []

    def prefetch(self, q):
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
    s = SessionStore()
    sid = s.create_session("s1")
    s.append_message(sid, Message(Role.USER, "hi"))
    s.append_message(sid, Message(Role.ASSISTANT, tool_calls=[ToolCall("c1", "echo", {"text": "x"})]))
    s.append_message(sid, Message(Role.TOOL, tool_result=ToolResult("c1", "echo", "x")))
    msgs = s.get_messages(sid)
    assert [m.role for m in msgs] == [Role.USER, Role.ASSISTANT, Role.TOOL]
    assert msgs[1].tool_calls[0].name == "echo"
    assert msgs[2].tool_result.content == "x"


def test_branch_forks_history_and_fires_switch():
    h = RecordingHooks()
    s = SessionStore(hooks=h)
    sid = s.create_session("s1")
    s.append_message(sid, Message(Role.USER, "hi"))
    new = s.branch(sid, "s2")
    assert [m.content for m in s.get_messages(new)] == ["hi"]
    assert h.switches[0][0] == "s2" and h.switches[0][2] is False


def test_reset_clears_and_fires_switch():
    h = RecordingHooks()
    s = SessionStore(hooks=h)
    sid = s.create_session("s1")
    s.append_message(sid, Message(Role.USER, "hi"))
    s.reset(sid)
    assert s.get_messages(sid) == []
    assert h.switches[-1][2] is True
