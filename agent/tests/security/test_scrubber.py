"""Tests for ``security/scrubber.py`` — the ported cross-chunk fence scrubber.

EN — A ``<memory-context>`` span split across deltas leaks nothing; an unclosed span is discarded on
flush; plain text passes through; a non-tag tail is emitted. 中文 — 跨 delta 切分的 ``<memory-context>`` span
不泄漏；未关闭 span 在 flush 时丢弃；纯文本透传；非标签尾部被发出。
"""
from jobpin_agent.security.scrubber import StreamingContextScrubber


def test_cross_chunk_split_no_leak():
    """A fence opened in one delta and closed in another leaks no fenced content.

    EN: 0 fenced leak. 中文：0 围栏泄漏。
    """
    s = StreamingContextScrubber()
    out = s.feed("Hello\n<memory-cont") + s.feed("ext>\nSECRET recall\n</memory-") + s.feed("context>\nBye")
    out += s.flush()
    assert "SECRET" not in out
    assert "Hello" in out and "Bye" in out


def test_unclosed_span_discarded_on_flush():
    """A stream that ends inside an unclosed fence discards the remainder.

    EN: leaking partial memory is worse than a truncated reply. 中文：泄漏部分记忆比截断答复更糟。
    """
    s = StreamingContextScrubber()
    out = s.feed("ok\n<memory-context>\nleaking secret...")
    out += s.flush()
    assert "leaking secret" not in out and "ok" in out


def test_plain_text_passes_through():
    """Plain text with no fence is emitted unchanged.

    EN: passthrough. 中文：透传。
    """
    s = StreamingContextScrubber()
    assert s.feed("just a normal answer") + s.flush() == "just a normal answer"


def test_non_tag_tail_emitted_on_flush():
    """A held-back fragment that turns out not to be a tag is emitted on flush.

    EN: partial '<mem' that never completes is surfaced. 中文：未完成的部分 '<mem' 最终被发出。
    """
    s = StreamingContextScrubber()
    out = s.feed("answer <mem")     # looks like a possible open tag → held back
    out += s.flush()
    assert out == "answer <mem"
