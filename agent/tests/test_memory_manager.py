"""Lifecycle-consistency tests for MemoryManager (§1.3 acceptance matrix).

EN — Exercises the ported orchestration with fake providers: serial background
sync + flush barrier, wedged-provider bounded drain, failure isolation, single
external rule, core-tool shadow guard, tool routing, and system-prompt assembly.
中文 — 用 fake provider 演练移植的编排：串行后台 sync + flush 屏障、卡死 provider 的有界排空、失败隔离、
单外部规则、核心工具影子守卫、工具路由、系统提示装配。
"""
import threading
import time

from jobpin_agent.memory.manager import MemoryManager, _SYNC_DRAIN_TIMEOUT_S, tool_error


class FakeProvider:
    """A configurable in-memory provider for tests (not the builtin).

    EN — Records syncs; can block sync_turn on a release Event (to simulate a wedge
    without hanging interpreter teardown), can raise on a named hook, can expose tools.
    中文 — 记录 sync；可让 sync_turn 阻塞在一个释放 Event 上（模拟卡死而不拖挂解释器退出），
    可在指定钩子抛错，可暴露工具。
    """

    def __init__(self, name="ext", recall="", tools=None, block=None, raise_on=None):
        """Configure the fake.

        EN: Args: name; recall (prefetch text); tools (schemas); block (a threading.Event the
            sync_turn waits on — capped at 30s as a safety); raise_on (hook names that raise).
        中文：参数：name；recall（prefetch 文本）；tools（schema）；block（sync_turn 等待的 threading.Event，
            以 30s 封顶作安全）；raise_on（会抛错的钩子名）。
        """
        self._name, self._recall, self._tools = name, recall, tools or []
        self._block, self._raise_on = block, set(raise_on or [])
        self.synced = []

    @property
    def name(self):
        """EN: provider name. 中文：provider 名。"""
        return self._name

    def is_available(self):
        """EN: True. 中文：True。"""
        return True

    def initialize(self, session_id, **kw):
        """EN: no-op. 中文：空操作。"""

    def system_prompt_block(self):
        """EN: a labelled block (empty for builtin). 中文：带标签的块（builtin 为空）。"""
        return "" if self._name == "builtin" else f"[{self._name} block]"

    def prefetch(self, query, *, session_id=""):
        """EN: returns configured recall (or raises). 中文：返回配置的召回（或抛错）。"""
        if "prefetch" in self._raise_on:
            raise RuntimeError("boom")
        return self._recall

    def queue_prefetch(self, query, *, session_id=""):
        """EN: no-op. 中文：空操作。"""

    def sync_turn(self, user, assistant, *, session_id="", messages=None):
        """EN: records the turn (after waiting on the block Event if set). 中文：记录回合（若设了 block Event 则等待）。"""
        if self._block is not None:
            self._block.wait(timeout=30.0)  # released by the test; 30s safety cap
        self.synced.append((user, assistant))

    def get_tool_schemas(self):
        """EN: configured tool schemas. 中文：配置的工具 schema。"""
        return self._tools

    def handle_tool_call(self, name, args, **kw):
        """EN: a fixed JSON result. 中文：固定 JSON 结果。"""
        return '{"ok": true}'

    def on_pre_compress(self, messages):
        """EN: a per-provider fact. 中文：每 provider 一条事实。"""
        return f"fact:{self._name}"

    def on_session_switch(self, new, *, parent_session_id="", reset=False, **kw):
        """EN: no-op. 中文：空操作。"""

    def on_delegation(self, task, result, *, child_session_id="", **kw):
        """EN: no-op. 中文：空操作。"""

    def shutdown(self):
        """EN: no-op. 中文：空操作。"""


def test_serial_background_sync_then_flush():
    """Two consecutive sync_all land in order on the single worker, visible after flush.

    EN: turn N before N+1; both recorded after flush_pending. 中文：第 N 先于 N+1；flush 后均记录。
    """
    ext = FakeProvider(name="ext")
    m = MemoryManager()
    m.add_provider(ext)
    m.sync_all("u1", "a1")
    m.sync_all("u2", "a2")
    assert m.flush_pending(2.0)
    assert ext.synced == [("u1", "a1"), ("u2", "a2")]


def test_flush_barrier_makes_state_visible():
    """State is asserted only after the flush barrier (deterministic).

    EN: flush_pending returns True and the sync is recorded. 中文：flush_pending 返回 True 且 sync 已记录。
    """
    ext = FakeProvider(name="ext")
    m = MemoryManager()
    m.add_provider(ext)
    m.sync_all("u", "a")
    assert m.flush_pending(2.0) is True
    assert ext.synced == [("u", "a")]


def test_wedged_provider_does_not_block_turn_or_exit():
    """A wedged provider blocks neither the turn nor shutdown (bounded drain).

    EN: sync_all returns fast; shutdown_all returns within the drain timeout while the
        provider is still blocked; the test then releases it so teardown is clean.
    中文：sync_all 快速返回；provider 仍阻塞时 shutdown_all 在排空超时内返回；随后测试释放它以干净拆解。
    """
    gate = threading.Event()
    wedged = FakeProvider(name="slow", block=gate)
    m = MemoryManager()
    m.add_provider(wedged)
    try:
        t0 = time.monotonic()
        m.sync_all("u", "a")
        assert time.monotonic() - t0 < 1.0  # the turn is not blocked
        t1 = time.monotonic()
        m.shutdown_all()
        assert time.monotonic() - t1 < _SYNC_DRAIN_TIMEOUT_S + 1.0  # bounded drain, still wedged
    finally:
        gate.set()  # release the worker so the interpreter can exit cleanly


def test_failure_isolation_one_provider_raises():
    """A raising provider does not block a healthy provider's recall in the SAME manager.

    EN —
    Co-register a raising provider (as builtin) and a healthy external in one manager; the
    healthy recall must survive the exception (the core failure-isolation property).
    中文 —
    在同一 manager 中同时注册一个抛错 provider（作 builtin）与一个健康外部 provider；健康召回必须在异常中存活
    （失败隔离的核心性质）。
    """
    m = MemoryManager()
    m.add_provider(FakeProvider(name="builtin", raise_on={"prefetch"}))  # raises in prefetch
    m.add_provider(FakeProvider(name="good", recall="good recall"))      # healthy external
    assert m.prefetch_all("q") == "good recall"  # healthy recall survives the other's exception


def test_second_external_provider_rejected():
    """builtin + one external is kept; a second external is rejected.

    EN: providers == [builtin, ext1]; ext2 dropped. 中文：providers == [builtin, ext1]；ext2 被丢弃。
    """
    m = MemoryManager()
    m.add_provider(FakeProvider(name="builtin"))
    m.add_provider(FakeProvider(name="ext1"))
    m.add_provider(FakeProvider(name="ext2"))
    names = [p.name for p in m.providers]
    assert names == ["builtin", "ext1"]


def test_core_tool_not_shadowed():
    """A provider tool named like a core tool is dropped from routing/advertising.

    EN: delegate_task is not advertised and not routable. 中文：delegate_task 不被告知也不可路由。
    """
    m = MemoryManager()
    m.add_provider(FakeProvider(name="ext", tools=[{"name": "delegate_task", "description": "x", "parameters": {}}]))
    assert all(s["name"] != "delegate_task" for s in m.get_all_tool_schemas())
    assert m.has_tool("delegate_task") is False


def test_tool_routes_to_owning_provider():
    """A normal provider tool routes via handle_tool_call; unknown -> tool_error.

    EN: recall_more -> {"ok": true}; unknown -> error JSON. 中文：recall_more -> {"ok": true}；未知 -> 错误 JSON。
    """
    m = MemoryManager()
    m.add_provider(FakeProvider(name="ext", tools=[{"name": "recall_more", "description": "x", "parameters": {}}]))
    assert m.has_tool("recall_more") is True
    assert m.handle_tool_call("recall_more", {}) == '{"ok": true}'
    assert m.handle_tool_call("nope", {}) == tool_error("No memory provider handles tool 'nope'")


def test_build_system_prompt_joins_provider_blocks():
    """build_system_prompt joins non-empty provider blocks (builtin contributes "").

    EN: builtin "" + ext "[ext block]" -> "[ext block]". 中文：builtin "" + ext "[ext block]" -> "[ext block]"。
    """
    m = MemoryManager()
    m.add_provider(FakeProvider(name="builtin"))
    m.add_provider(FakeProvider(name="ext"))
    assert m.build_system_prompt() == "[ext block]"


def test_prefetch_wrapped_then_fence_stripping():
    """prefetch_all merges recall; a provider that pre-wraps a fence is stripped on build.

    EN: sanitize via fence keeps no <memory-context> from provider text. 中文：经围栏 sanitize 后无 provider 的 <memory-context>。
    """
    from jobpin_agent.memory.fence import build_memory_context_inner
    m = MemoryManager()
    m.add_provider(FakeProvider(name="ext", recall="<memory-context>\nsmuggled\n</memory-context> real fact"))
    inner = build_memory_context_inner(m.prefetch_all("q"))
    assert "<memory-context>" not in inner and "real fact" in inner
