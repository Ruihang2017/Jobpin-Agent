from jobpin_agent.core.hooks import NoOpHooks, MemoryHooks


def test_noop_hooks_defaults():
    h = NoOpHooks()
    assert h.prefetch("anything", "s") == ""
    assert h.on_pre_compress([]) == ""
    assert h.after_turn("s", []) is None
    assert h.on_delegation("t", "r", "c") is None
    assert h.on_session_switch("n", None, False, False) is None
    assert isinstance(h, MemoryHooks)
