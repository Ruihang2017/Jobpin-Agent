"""Tests for the MemoryManagerHooks adapter + the end-to-end "closes the loop" proof.

EN — The adapter delegates to the Manager and wraps prefetch as the inner block;
the end-to-end test wires a real §1.1 Agent (FakeProvider model) to a memory backend
and asserts the Org snapshot + fenced recall reach the model, with NO loop change.
中文 — 适配器委派给 Manager 并将 prefetch 包成内层块；端到端测试将真实 §1.1 Agent（FakeProvider 模型）接到记忆
后端，断言 Org 快照与围栏召回到达模型，且不改动循环。
"""
from jobpin_agent.core.agent_loop import Agent
from jobpin_agent.core.hooks import MemoryHooks
from jobpin_agent.core.messages import Message, ModelResponse, Role
from jobpin_agent.core.model.fake_provider import FakeProvider as FakeModel
from jobpin_agent.core.session_store import SessionStore
from jobpin_agent.core.system_prompt import SystemPromptParts
from jobpin_agent.core.tools import ToolRegistry
from jobpin_agent.memory.composition import build_memory_backend
from jobpin_agent.memory.manager import MemoryManager
from jobpin_agent.memory.manager_hooks import MemoryManagerHooks
from tests.test_memory_manager import FakeProvider  # reuse the recording fake provider


def test_adapter_satisfies_protocol_and_wraps_prefetch():
    """The adapter is a MemoryHooks and wraps recall as the inner fenced block.

    EN: isinstance(MemoryHooks); prefetch returns the system note + recall, no outer tags.
    中文：isinstance(MemoryHooks)；prefetch 返回系统注记 + 召回，无外层标签。
    """
    m = MemoryManager()
    m.add_provider(FakeProvider(name="ext", recall="cand prefers remote"))
    h = MemoryManagerHooks(m)
    assert isinstance(h, MemoryHooks)
    inner = h.prefetch("find remote devs", "s1")
    assert "[System note:" in inner and "cand prefers remote" in inner and "<memory-context>" not in inner


def test_after_turn_syncs_last_user_and_assistant():
    """after_turn extracts the last user/assistant text and syncs them (visible after flush).

    EN: ext.synced == [("hello", "hi there")] after flush_pending. 中文：flush 后 ext.synced == [("hello", "hi there")]。
    """
    ext = FakeProvider(name="ext")
    m = MemoryManager()
    m.add_provider(ext)
    h = MemoryManagerHooks(m)
    msgs = [Message(Role.USER, content="hello"), Message(Role.ASSISTANT, content="hi there")]
    h.after_turn("s1", msgs)
    assert m.flush_pending(2.0)
    assert ext.synced == [("hello", "hi there")]


def test_on_pre_compress_aggregates_provider_facts():
    """on_pre_compress aggregates the providers' returned facts.

    EN: a provider returning 'fact:ext' surfaces in the aggregate. 中文：返回 'fact:ext' 的 provider 出现在聚合中。
    """
    m = MemoryManager()
    m.add_provider(FakeProvider(name="ext"))
    h = MemoryManagerHooks(m)
    assert "fact:ext" in h.on_pre_compress([Message(Role.USER, content="x")])


def test_agent_system_prompt_contains_org_memory_and_fenced_recall(tmp_path):
    """End-to-end: the §1.1 Agent's model sees the Org snapshot + fenced recall (no loop change).

    EN —
    Seed ORG.md, add a fake recall provider, wire a real Agent with the backend's
    hooks + snapshot/provider slots; assert the model's first request contains the Org
    standard and a <memory-context> recall block, and the turn syncs after flush.
    中文 —
    预置 ORG.md，加入 fake 召回 provider，用后端的 hooks + 快照/provider 槽位接一个真实 Agent；断言模型首个请求含 Org
    标准与 <memory-context> 召回块，且回合在 flush 后完成同步。
    """
    mem = tmp_path / "mem"
    mem.mkdir()
    (mem / "ORG.md").write_text("Score for demonstrated impact, not tenure.", encoding="utf-8")
    recall = FakeProvider(name="ext", recall="cand_7f3a prefers remote")
    backend = build_memory_backend(mem, extra_providers=[recall])

    parts = SystemPromptParts(
        memory_snapshot=backend.memory_snapshot(),
        provider_block=backend.provider_block(),
    )
    store = SessionStore(":memory:")
    sid = store.create_session()
    model = FakeModel(script=[ModelResponse(text="ok")])  # one plain-answer turn
    agent = Agent(model, ToolRegistry(), store, hooks=backend.hooks, parts=parts)

    result = agent.run_turn(sid, "what's our hiring bar?")
    assert result.text == "ok"

    sent = model.calls[0]  # the messages the model received on the only call
    blob = "\n".join(m.content for m in sent)
    assert "Score for demonstrated impact, not tenure." in blob  # Org snapshot reached the prompt
    assert "<memory-context>" in blob and "cand_7f3a prefers remote" in blob  # fenced recall reached the prompt

    assert backend.manager.flush_pending(2.0)
    assert recall.synced == [("what's our hiring bar?", "ok")]  # the turn synced through the seam
