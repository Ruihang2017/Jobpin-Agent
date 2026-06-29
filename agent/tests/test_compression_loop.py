"""End-to-end §1.6 compression through ``Agent.run_turn`` — opt-in, key fact survives, off = unchanged.

EN — A long session is compressed at the turn's top so a key early fact still reaches the model (in the
summary) while the bulk is folded; with no compressor the loop is unchanged. 中文 — 长会话在回合开头被压缩，
使关键早期事实仍到达模型（在摘要中）而主体被折叠；无压缩器时循环不变。
"""
from jobpin_agent.core.agent_loop import Agent
from jobpin_agent.core.compression import ContextCompressor
from jobpin_agent.core.messages import Message, ModelResponse, Role
from jobpin_agent.core.model.fake_provider import FakeProvider
from jobpin_agent.core.session_store import SessionStore
from jobpin_agent.core.tools import ToolRegistry


def test_long_session_compresses_at_turn_top_and_fact_survives():
    """An over-long history is folded; the early key fact survives in the composed prompt.

    EN: fact in model.calls[0]; history shrank. 中文：事实在 model.calls[0]；历史缩小。
    """
    store = SessionStore(":memory:")
    sid = store.create_session()
    for i in range(20):
        content = "Ada cleared to interview" if i == 1 else f"msg {i}"
        store.append_message(sid, Message(Role.USER, content=content))
    model = FakeProvider(script=[ModelResponse(text="ok")])
    agent = Agent(model, ToolRegistry(), store, compressor=ContextCompressor(max_messages=8, keep_recent=4))

    agent.run_turn(sid, "next question")

    sent = "\n".join(m.content for m in model.calls[0] if m.content)
    assert "Ada cleared to interview" in sent  # survived in the compressed summary
    assert len(store.get_messages(sid)) <= 8   # old bulk folded


def test_no_compressor_is_unchanged():
    """With no compressor the loop behaves exactly as §1.1–§1.5.

    EN: plain turn. 中文：普通回合。
    """
    store = SessionStore(":memory:")
    sid = store.create_session()
    model = FakeProvider(script=[ModelResponse(text="ok")])
    agent = Agent(model, ToolRegistry(), store)  # compressor defaults None
    out = agent.run_turn(sid, "hi")
    assert out.text == "ok"
