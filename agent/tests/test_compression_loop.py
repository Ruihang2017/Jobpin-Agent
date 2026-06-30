"""End-to-end §1.6 compression through ``Agent.run_turn`` — opt-in, key fact survives, off = unchanged.

EN — A long session is compressed at the turn's top so a key early fact still reaches the model (in the
summary) while the bulk is folded; with no compressor the loop is unchanged. 中文 — 长会话在回合开头被压缩，
使关键早期事实仍到达模型（在摘要中）而主体被折叠；无压缩器时循环不变。
"""
from jobpin_agent.core.agent_loop import Agent
from jobpin_agent.core.compression import ContextCompressor
from jobpin_agent.core.hooks import NoOpHooks
from jobpin_agent.core.messages import Message, ModelResponse, Role
from jobpin_agent.core.model.fake_provider import FakeProvider
from jobpin_agent.core.session_store import SessionStore
from jobpin_agent.core.tools import ToolRegistry


class _PreCompressHooks(NoOpHooks):
    """NoOpHooks but with a non-empty on_pre_compress (a provider-extracted fact).

    EN: returns the configured fact during pre-compression. 中文：压缩前返回配置的事实。
    """

    def __init__(self, fact: str) -> None:
        self._fact = fact

    def on_pre_compress(self, messages) -> str:
        """Return the configured pre-compression fact. EN/中文: returns the fact string."""
        return self._fact


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


def test_on_pre_compress_fact_survives_lossy_compression_through_run_turn():
    """End-to-end: a lossy summariser drops folded content, but the on_pre_compress fact reaches the model.

    EN — proves the §1.6 wiring end-to-end through run_turn (not just the unit path): the rescued fact is
    in the composed prompt after compression, while the old bulk is gone. 中文 — 经 run_turn 端到端证明 §1.6
    接线：被抢救的事实在压缩后出现在组装提示中，而旧主体消失。
    """
    def lossy_summarize(old_messages, facts):
        return "[lossy summary] " + (facts or "")

    store = SessionStore(":memory:")
    sid = store.create_session()
    for i in range(20):
        store.append_message(sid, Message(Role.USER, content=f"chatter {i}"))
    model = FakeProvider(script=[ModelResponse(text="ok")])
    compressor = ContextCompressor(max_messages=8, keep_recent=4, summarize_fn=lossy_summarize)
    agent = Agent(model, ToolRegistry(), store,
                  hooks=_PreCompressHooks("RESCUED FACT: Ada shortlisted"), compressor=compressor)

    agent.run_turn(sid, "next")

    sent = "\n".join(m.content for m in model.calls[0] if m.content)
    assert "RESCUED FACT: Ada shortlisted" in sent   # survived a LOSSY fold only via on_pre_compress capture
    assert "chatter 0" not in sent                    # the lossy summariser dropped the old bulk


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
