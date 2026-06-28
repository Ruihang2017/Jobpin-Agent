"""Tests for the §1.4 minimal CompositeMemoryProvider.

EN — broadcast prefetch merges + dedups; sole external on a real Manager; unicast vs fan-out sync;
reverse-order shutdown. 中文 — 广播 prefetch 归并 + 去重；在真实 Manager 上为唯一外部；单播 vs 扇出 sync；
逆序 shutdown。
"""
from jobpin_agent.memory.manager import MemoryManager
from jobpin_agent.memory.providers.composite import CompositeMemoryProvider
from jobpin_agent.memory.store import ENTRY_DELIMITER


class FakeSub:
    """A controllable sub-provider for Composite tests.

    EN — Returns a fixed recall; records syncs; records its shutdown order via a shared list.
    中文 — 返回固定召回；记录 sync；经共享列表记录其 shutdown 顺序。
    """

    def __init__(self, name, entity_type, recall="", order_log=None):
        """Args: name; entity_type; recall; order_log (shared list). 中文：参数：见英文。"""
        self._name, self.entity_type, self._recall = name, entity_type, recall
        self._order = order_log
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
        """EN: a labelled block. 中文：带标签的块。"""
        return f"[{self._name}]"

    def prefetch(self, query, *, session_id=""):
        """EN: the fixed recall. 中文：固定召回。"""
        return self._recall

    def queue_prefetch(self, query, *, session_id=""):
        """EN: no-op. 中文：空操作。"""

    def sync_turn(self, user, assistant, *, session_id="", messages=None, **kw):
        """EN: record the synced turn. 中文：记录已同步回合。"""
        self.synced.append((user, assistant))

    def get_tool_schemas(self):
        """EN: no tools. 中文：无工具。"""
        return []

    def on_pre_compress(self, messages):
        """EN: no facts. 中文：无事实。"""
        return ""

    def on_session_switch(self, *a, **k):
        """EN: no-op. 中文：空操作。"""

    def on_delegation(self, *a, **k):
        """EN: no-op. 中文：空操作。"""

    def on_memory_write(self, *a, **k):
        """EN: no-op. 中文：空操作。"""

    def backup_paths(self):
        """EN: none. 中文：无。"""
        return []

    def shutdown(self):
        """EN: record shutdown order. 中文：记录 shutdown 顺序。"""
        if self._order is not None:
            self._order.append(self._name)


def test_prefetch_merges_and_dedups():
    """Broadcast prefetch merges sub-provider entries and dedups the shared one.

    EN: A="e1 § shared", B="shared § e2" -> "e1 § shared § e2" (shared once).
    中文：A="e1 § shared"、B="shared § e2" -> "e1 § shared § e2"（shared 一次）。
    """
    a = FakeSub("semantic", "semantic", recall=f"entry one{ENTRY_DELIMITER}shared")
    b = FakeSub("candidate", "candidate", recall=f"shared{ENTRY_DELIMITER}entry two")
    c = CompositeMemoryProvider([a, b])
    merged = c.prefetch("q")
    assert merged == f"entry one{ENTRY_DELIMITER}shared{ENTRY_DELIMITER}entry two"


def test_budget_truncates():
    """char_budget keeps entries in order until the cap.

    EN: a tiny budget keeps only the first entry. 中文：极小预算只保留第一条。
    """
    a = FakeSub("semantic", "semantic", recall=f"first{ENTRY_DELIMITER}second{ENTRY_DELIMITER}third")
    c = CompositeMemoryProvider([a], char_budget=5)
    assert c.prefetch("q") == "first"


def test_registers_as_sole_external_on_manager():
    """The Composite is the single external; a second external is rejected.

    EN: [builtin, composite]; a further external dropped. 中文：[builtin, composite]；再一个外部被丢弃。
    """
    m = MemoryManager()

    class _Builtin(FakeSub):
        @property
        def name(self):
            return "builtin"

    m.add_provider(_Builtin("builtin", "builtin"))
    m.add_provider(CompositeMemoryProvider([FakeSub("semantic", "semantic")]))
    m.add_provider(FakeSub("rogue", "rogue"))
    assert [p.name for p in m.providers] == ["builtin", "composite"]


def test_sync_unicast_vs_fanout():
    """sync_turn unicasts when entity_type is given, else fans out; non-primary skipped.

    EN: entity_type="candidate" -> only candidate; no entity_type -> both; subagent -> none.
    中文：entity_type="candidate" -> 仅 candidate；无 entity_type -> 两者；subagent -> 无。
    """
    a = FakeSub("semantic", "semantic")
    b = FakeSub("candidate", "candidate")
    c = CompositeMemoryProvider([a, b])
    c.sync_turn("u", "a", entity_type="candidate")
    assert a.synced == [] and b.synced == [("u", "a")]
    c.sync_turn("u2", "a2")  # fan out
    assert a.synced == [("u2", "a2")] and b.synced == [("u", "a"), ("u2", "a2")]
    c.sync_turn("u3", "a3", agent_context="subagent")  # skipped
    assert a.synced == [("u2", "a2")]


def test_shutdown_reverse_order_and_blocks():
    """shutdown closes sub-providers in reverse order; system_prompt_block concatenates.

    EN: order == [b, a]; block == "[a]\n\n[b]". 中文：顺序 == [b, a]；块 == "[a]\n\n[b]"。
    """
    order = []
    a = FakeSub("a", "semantic", order_log=order)
    b = FakeSub("b", "candidate", order_log=order)
    c = CompositeMemoryProvider([a, b])
    assert c.system_prompt_block() == "[a]\n\n[b]"
    c.shutdown()
    assert order == ["b", "a"]
