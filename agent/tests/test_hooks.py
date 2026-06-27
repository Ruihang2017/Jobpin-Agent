"""Tests for the memory-hooks seam.

EN —
Confirms ``NoOpHooks`` is inert and satisfies the ``MemoryHooks`` protocol.
中文 —
确认 ``NoOpHooks`` 为空操作且满足 ``MemoryHooks`` 协议。
"""
from jobpin_agent.core.hooks import NoOpHooks, MemoryHooks


def test_noop_hooks_defaults():
    """Every NoOp hook returns its inert default and matches the protocol.

    EN: prefetch/on_pre_compress -> ""; the rest -> None; isinstance(MemoryHooks).
    中文：prefetch/on_pre_compress -> ""；其余 -> None；isinstance(MemoryHooks)。
    """
    h = NoOpHooks()
    assert h.prefetch("anything", "s") == ""
    assert h.on_pre_compress([]) == ""
    assert h.after_turn("s", []) is None
    assert h.on_delegation("t", "r", "c") is None
    assert h.on_session_switch("n", None, False, False) is None
    assert isinstance(h, MemoryHooks)
