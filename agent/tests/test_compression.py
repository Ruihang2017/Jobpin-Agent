"""Tests for ``core/compression.py`` + ``SessionStore.compact`` — pre-compression fact-injection (§1.6).

EN — Threshold; folding old into a summary that keeps recent + merges on_pre_compress facts + preserves
old-message content; a gated-persist rejection does not crash. 中文 — 阈值；把旧消息折叠为保留最近 + 并入
on_pre_compress 事实 + 保留旧消息内容的摘要；门控持久化拒绝不崩溃。
"""
from jobpin_agent.core.compression import ContextCompressor, default_summarize
from jobpin_agent.core.messages import Message, Role
from jobpin_agent.core.session_store import SessionStore


class _Hooks:
    """A duck-typed MemoryHooks returning a fixed pre-compression fact.

    EN: Args: fact. 中文：参数：fact。
    """

    def __init__(self, fact: str) -> None:
        self._f = fact

    def on_pre_compress(self, messages) -> str:
        """Return the fixed fact. EN/中文: returns the configured fact string."""
        return self._f


def _seed(store, sid, n):
    """Append n user/assistant turns; turn 2 carries a distinctive key fact.

    EN: helper. 中文：辅助。
    """
    for i in range(n):
        content = "fact Ada knows Kafka" if i == 2 else f"turn {i}"
        store.append_message(sid, Message(Role.USER, content=content))
        store.append_message(sid, Message(Role.ASSISTANT, content=f"ack {i}"))


def test_should_compress_threshold():
    """should_compress fires only above max_messages.

    EN: threshold. 中文：阈值。
    """
    c = ContextCompressor(max_messages=4)
    assert not c.should_compress([1, 2, 3, 4])
    assert c.should_compress([1, 2, 3, 4, 5])


def test_compress_folds_old_keeps_recent_and_merges_facts():
    """compress writes a summary (keeping recent) that holds the old fact AND the provider facts.

    EN: summary contains both. 中文：摘要同时包含两者。
    """
    store = SessionStore(":memory:")
    sid = store.create_session()
    _seed(store, sid, 8)  # 16 messages
    c = ContextCompressor(max_messages=6, keep_recent=4)
    res = c.compress(sid, store, _Hooks("KEY FACT: Ada cleared to interview"))
    msgs = store.get_messages(sid)
    assert res.compressed and len(msgs) == 5  # 1 summary + 4 recent
    assert msgs[0].role == Role.SYSTEM
    assert "Ada knows Kafka" in msgs[0].content  # old-message digest preserved
    assert "KEY FACT: Ada cleared to interview" in msgs[0].content  # provider facts merged


def test_gated_persist_rejection_does_not_crash():
    """A persist_fn that raises (gate rejection) is swallowed; the summary is still written.

    EN: persisted False, no crash. 中文：persisted 为 False，不崩溃。
    """
    store = SessionStore(":memory:")
    sid = store.create_session()
    _seed(store, sid, 8)

    def reject(_facts):
        raise RuntimeError("rejected:no_consent")

    c = ContextCompressor(max_messages=6, keep_recent=4, persist_fn=reject)
    res = c.compress(sid, store, _Hooks("a fact"))
    assert res.compressed and res.persisted is False
    assert store.get_messages(sid)[0].role == Role.SYSTEM


def test_compact_noop_when_short():
    """compact is a no-op when there is nothing to fold.

    EN: short history unchanged. 中文：短历史不变。
    """
    store = SessionStore(":memory:")
    sid = store.create_session()
    store.append_message(sid, Message(Role.USER, content="hi"))
    store.compact(sid, Message(Role.SYSTEM, content="summary"), keep_recent=6)
    assert len(store.get_messages(sid)) == 1


def test_lossy_summariser_loses_old_content_but_pre_compress_fact_survives():
    """With a LOSSY summariser the captured on_pre_compress fact is what survives — proving the wiring's value.

    EN — the §1.6 point is rescuing a fact a lossy summariser would otherwise drop. A lossy summarize_fn
    keeps only the captured facts; the old turn content is gone, but the on_pre_compress fact remains.
    中文 — §1.6 的要点是抢救有损摘要会丢弃的事实。有损 summarize_fn 仅保留捕获的事实；旧回合内容消失，但
    on_pre_compress 事实留存。
    """
    def lossy_summarize(old_messages, facts):
        return "[lossy summary] " + (facts or "")  # deliberately DROPS the folded message content

    store = SessionStore(":memory:")
    sid = store.create_session()
    _seed(store, sid, 8)  # turn 2 carries "fact Ada knows Kafka" in the OLD (folded) region
    c = ContextCompressor(max_messages=6, keep_recent=4, summarize_fn=lossy_summarize)
    c.compress(sid, store, _Hooks("RESCUED: Ada cleared to interview"))
    summary = store.get_messages(sid)[0].content
    assert "RESCUED: Ada cleared to interview" in summary   # survived ONLY via capture+merge
    assert "fact Ada knows Kafka" not in summary            # the lossy summariser dropped old content
    assert "turn 0" not in summary


def test_default_summarize_is_fact_preserving():
    """default_summarize includes both the provider facts and a digest of the old turns.

    EN: both present. 中文：两者皆在。
    """
    old = [Message(Role.USER, content="candidate Ada strong on Kafka")]
    out = default_summarize(old, "RETAINED: shortlist Ada")
    assert "RETAINED: shortlist Ada" in out and "Ada strong on Kafka" in out
