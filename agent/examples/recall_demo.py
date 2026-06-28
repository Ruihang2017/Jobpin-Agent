"""End-to-end §1.4 demo — résumé → vectorize → fenced recall through the Composite (offline).

EN —
Ingests a couple of résumés into a ``CandidateMemoryProvider`` and a knowledge-base chunk into a
``SemanticRAGProvider``, wraps both in the minimal ``CompositeMemoryProvider``, registers the Composite
as the **sole external** provider on a §1.3 ``MemoryManager``, builds the §1.3 ``MemoryManagerHooks``,
and runs ONE real §1.1 ``Agent`` turn with a scripted ``FakeProvider`` model. It shows that an NL query's
recall — the right candidate, with a **back-to-source citation** — reaches the model as a
``<memory-context>`` message, with **no change to ``agent_loop.py``**. No key, no network.

中文 —
把两份简历 ingest 进 ``CandidateMemoryProvider``、一段知识库 ingest 进 ``SemanticRAGProvider``，用最小
``CompositeMemoryProvider`` 包裹两者，将 Composite 注册为 §1.3 ``MemoryManager`` 上的**唯一外部** provider，构建 §1.3
``MemoryManagerHooks``，并用脚本化 ``FakeProvider`` 模型运行一个真实 §1.1 ``Agent`` 回合。它展示一个 NL 查询的召回——
正确候选人 + **回到来源引用**——以 ``<memory-context>`` 消息到达模型，且**不改动 ``agent_loop.py``**。无密钥、无网络。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpin_agent.core.agent_loop import Agent
from jobpin_agent.core.messages import ModelResponse
from jobpin_agent.core.model.fake_provider import FakeProvider as FakeModel
from jobpin_agent.core.session_store import SessionStore
from jobpin_agent.core.system_prompt import SystemPromptParts
from jobpin_agent.core.tools import ToolRegistry
from jobpin_agent.memory.embedding import embed_version, hashing_embedder
from jobpin_agent.memory.manager import MemoryManager
from jobpin_agent.memory.manager_hooks import MemoryManagerHooks
from jobpin_agent.memory.providers.candidate import CandidateMemoryProvider
from jobpin_agent.memory.providers.composite import CompositeMemoryProvider
from jobpin_agent.memory.providers.semantic import SemanticRAGProvider
from jobpin_agent.memory.structured import CandidateRow, CandidateStructuredStore
from jobpin_agent.memory.vector.store import SqliteVectorStore

DIM = 256
KEY = "acme:apac:candidate:cand_7f3a"


def run_demo() -> dict:
    """Run the §1.4 end-to-end recall demo and return a summary dict.

    EN —
    Returns: ``{"recall_in_prompt", "has_citation", "fenced", "answer"}``.
    中文 —
    返回：``{"recall_in_prompt", "has_citation", "fenced", "answer"}``。
    """
    embed = hashing_embedder(DIM)
    ver = embed_version("hash", DIM)

    candidate = CandidateMemoryProvider(SqliteVectorStore(), CandidateStructuredStore(), embed,
                                        embed_model="hash", embed_version=ver, k=3)
    candidate.ingest(
        CandidateRow(KEY, name="Ada Lovelace", skills=["python", "distributed"], years=7, work_rights=True),
        [(f"{KEY}#0", "Senior Python engineer; designed distributed systems at scale."),
         (f"{KEY}#1", "Led a Kubernetes platform migration.")],
    )
    candidate.ingest(
        CandidateRow("acme:apac:candidate:cand_b2", name="Bo", skills=["sales"], years=4),
        [("acme:apac:candidate:cand_b2#0", "Enterprise sales lead, quota over-achiever.")],
    )

    semantic = SemanticRAGProvider(SqliteVectorStore(), embed, embed_model="hash", embed_version=ver, k=2)
    semantic.ingest("kb", "Score SWE candidates on demonstrated impact, not tenure.",
                    memory_key="acme:apac:semantic:kb", source_ref="kb#1")

    composite = CompositeMemoryProvider([semantic, candidate])
    manager = MemoryManager()
    manager.add_provider(composite)  # the sole external provider
    hooks = MemoryManagerHooks(manager)

    parts = SystemPromptParts(memory_snapshot="", provider_block=manager.build_system_prompt())
    store = SessionStore(":memory:")
    sid = store.create_session()
    model = FakeModel(script=[ModelResponse(text="Ada Lovelace is the strongest match.")])
    agent = Agent(model, ToolRegistry(), store, hooks=hooks, parts=parts)

    result = agent.run_turn(sid, "find a python distributed-systems engineer")
    sent = "\n".join(m.content for m in model.calls[0])
    return {
        "recall_in_prompt": KEY in sent,
        "has_citation": f"{KEY}#0" in sent and "memory_key:" in sent,
        "fenced": "<memory-context>" in sent,
        "answer": result.text,
    }


if __name__ == "__main__":  # pragma: no cover
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print(json.dumps(run_demo(), ensure_ascii=False, indent=2))
