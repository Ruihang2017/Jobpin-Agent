"""Thin hiring vertical slice — a REAL model recalls candidates and explains a shortlist.

EN —
The first end-to-end "it actually works": ingest a few **synthetic** résumés into the §1.4
``CandidateMemoryProvider`` (+ an org rubric into a ``SemanticRAGProvider``), wrap them in the §1.4
``CompositeMemoryProvider``, drive that through the §1.3 ``MemoryManager`` + ``MemoryManagerHooks``, and
attach it to a §1.1 ``Agent`` — **with no change to the loop**. Ask a hiring question and the model recalls
the right candidates (semantically, with a real embedder) and returns an explainable, **cited**,
**HITL-framed** shortlist. With ``OPENAI_API_KEY`` set (``agent/.env``) it uses a real model + real
embeddings; offline it falls back to the fake model + the lexical hashing embedder so the wiring still runs.

Privacy: **synthetic résumés only** — real candidate PII to a cloud model must first go through the
de-identification pipeline (§1.11), which is not built. Local-first remains the default; this is an opt-in
BYO-key dev/pilot path. Governance (§1.5), the real threat scan (§1.6), résumé parsing (§1.11), a real HITL
workflow (§1.7), and the model router (§1.11) are deferred behind the seams already built.

Run from ``agent/``: ``python examples/hiring_slice_demo.py``

中文 —
首个端到端“真正能用”：把几份**合成**简历 ingest 进 §1.4 ``CandidateMemoryProvider``（+ 一条组织评分细则进
``SemanticRAGProvider``），用 §1.4 ``CompositeMemoryProvider`` 包裹，经 §1.3 ``MemoryManager`` +
``MemoryManagerHooks`` 驱动，并接到 §1.1 ``Agent``——**不改动循环**。提出招聘问题，模型即召回正确候选人（用真实嵌入器
做语义召回）并返回可解释、**带引用**、**HITL 框定**的候选名单。设置 ``OPENAI_API_KEY``（``agent/.env``）时用真实模型 +
真实嵌入；离线时回退到 fake 模型 + 词面哈希嵌入器，使接线仍可运行。

隐私：**仅合成简历**——真实候选人 PII 发往云模型须先经去标识化流水线（§1.11，尚未构建）。本地优先仍为默认；这是
可选的 BYO-key 开发/试点路径。治理（§1.5）、真实威胁扫描（§1.6）、简历解析（§1.11）、真实 HITL 工作流（§1.7）与
模型路由（§1.11）均在已构建的接缝之后推迟。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow `python agent/examples/hiring_slice_demo.py` without setting PYTHONPATH.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpin_agent.core.agent_loop import Agent
from jobpin_agent.core.config import CoreConfig
from jobpin_agent.core.messages import ModelResponse
from jobpin_agent.core.model.fake_provider import FakeProvider
from jobpin_agent.core.model.openai_provider import OpenAIProvider
from jobpin_agent.core.session_store import SessionStore
from jobpin_agent.core.system_prompt import SystemPromptParts
from jobpin_agent.core.tools import ToolRegistry
from jobpin_agent.core.tracing import Tracer
from jobpin_agent.memory.embedding import hashing_embedder, openai_embedder
from jobpin_agent.memory.manager import MemoryManager
from jobpin_agent.memory.manager_hooks import MemoryManagerHooks
from jobpin_agent.memory.providers.candidate import CandidateMemoryProvider
from jobpin_agent.memory.providers.composite import CompositeMemoryProvider
from jobpin_agent.memory.providers.semantic import SemanticRAGProvider
from jobpin_agent.memory.structured import CandidateRow, CandidateStructuredStore
from jobpin_agent.memory.vector.store import SqliteVectorStore

ADA_KEY = "acme:apac:candidate:cand_ada"

# Synthetic résumés (NOT real people). The distinctive content lives in the PROSE, not the columns —
# so a fitting recall must come from the vector store, which the structured columns could not answer.
RESUMES = [
    (CandidateRow(ADA_KEY, name="Ada Lovelace", skills=["go", "kafka"], years=8,
                  location="Sydney", work_rights=True, consent_status="granted"),
     [(f"{ADA_KEY}#0",
       "Architected a globally-distributed, eventually-consistent payments ledger processing two million "
       "transactions per second; led a monolith-to-event-driven-microservices migration; mentored four "
       "engineers and overhauled the on-call rotation.")]),
    (CandidateRow("acme:apac:candidate:cand_grace", name="Grace Hopper", skills=["python", "postgres"],
                  years=10, location="Melbourne", work_rights=True, consent_status="granted"),
     [("acme:apac:candidate:cand_grace#0",
       "Built and operated the data platform; tuned PostgreSQL for high-volume OLTP; on-call lead known for "
       "rigorous incident reviews and reliability engineering.")]),
    (CandidateRow("acme:apac:candidate:cand_bo", name="Bo Tan", skills=["salesforce"], years=5,
                  location="Sydney", work_rights=True, consent_status="granted"),
     [("acme:apac:candidate:cand_bo#0",
       "Enterprise SaaS sales lead with consistent quota over-achievement across fintech accounts.")]),
]

ORG_RUBRIC = ("Score SWE candidates on demonstrated impact and operational maturity, not tenure; "
              "backend roles weight distributed-systems and reliability experience.")

QUESTION = ("We're hiring a senior backend engineer for a high-throughput payments platform. "
            "Who in our pool fits, and why? Cite the evidence, and flag this as a suggestion for human review.")


def hr_parts(provider_block: str) -> SystemPromptParts:
    """Build the HR hiring-assistant system-prompt sections (recommend-only, grounded, no protected attrs).

    EN: Args: provider_block (from ``manager.build_system_prompt()``). Returns: the HR ``SystemPromptParts``.
    中文：参数：provider_block（来自 ``manager.build_system_prompt()``）。返回：HR ``SystemPromptParts``。
    """
    return SystemPromptParts(
        org_policy="Jobpin Agent — an HR hiring assistant for an Australian employer.",
        compliance=(
            "Recommendations are SUGGESTIONS that require human confirmation (HITL); never make or imply a "
            "final hire/reject decision. Ground every claim in the candidate memory provided in the "
            "<memory-context>; cite the source (memory_key / source) for each claim; never invent "
            "qualifications. Do not consider or mention protected attributes (age, gender, race, marital or "
            "family status, health, etc.) or proxies for them."),
        role_permissions=(
            "Acting as a recruiter assistant. May: summarise, compare, and explain candidate fit with "
            "evidence. May not: contact candidates, send messages, or make decisions."),
        provider_block=provider_block,
    )


def build_hiring_slice(*, embed_fn, embed_version, model):
    """Assemble the full slice: ingest résumés + rubric, wire Composite→Manager→hooks→Agent.

    EN —
    Args: embed_fn (``EmbedFn``); embed_version (its pinned version string); model (a ``ModelProvider``).
    Returns: ``(agent, store, sid, manager, hooks)``. No new tools are registered — recall is automatic
    via the §1.3 prefetch hook; the model reasons over the fenced ``<memory-context>``.
    中文 —
    参数：embed_fn（``EmbedFn``）；embed_version（其固定版本串）；model（``ModelProvider``）。
    返回：``(agent, store, sid, manager, hooks)``。不注册新工具——召回经 §1.3 prefetch 钩子自动进行；模型在围栏
    ``<memory-context>`` 上推理。
    """
    candidate = CandidateMemoryProvider(SqliteVectorStore(), CandidateStructuredStore(), embed_fn,
                                        embed_model="demo", embed_version=embed_version, k=3)
    for row, chunks in RESUMES:
        candidate.ingest(row, chunks)
    semantic = SemanticRAGProvider(SqliteVectorStore(), embed_fn,
                                   embed_model="demo", embed_version=embed_version, k=2)
    semantic.ingest("rubric", ORG_RUBRIC, memory_key="acme:apac:semantic:rubric", source_ref="rubric#0")

    manager = MemoryManager()
    manager.add_provider(CompositeMemoryProvider([semantic, candidate]))  # the sole external provider
    hooks = MemoryManagerHooks(manager)

    parts = hr_parts(manager.build_system_prompt())
    store = SessionStore(":memory:")
    sid = store.create_session()
    agent = Agent(model, ToolRegistry(), store, hooks=hooks, parts=parts, tracer=Tracer())
    return agent, store, sid, manager, hooks


def run(question: str, *, embed_fn, embed_version, model) -> dict:
    """Build the slice and run one hiring turn; return the answer + recall facts.

    EN —
    Args: question; embed_fn; embed_version; model. Returns:
    ``{"answer", "recalled_candidate", "has_citation", "recall"}`` — ``recall`` is the fenced inner block
    that was injected into the prompt (model-agnostic, so it works for both the fake and the real model).
    中文 —
    参数：question；embed_fn；embed_version；model。返回：``{"answer", "recalled_candidate", "has_citation",
    "recall"}``——``recall`` 是注入提示的围栏内层块（与模型无关，故对 fake 与真实模型都适用）。
    """
    agent, store, sid, manager, hooks = build_hiring_slice(
        embed_fn=embed_fn, embed_version=embed_version, model=model)
    recall = hooks.prefetch(question, sid)  # the inner block the loop will fence into the prompt
    result = agent.run_turn(sid, question)
    return {
        "answer": result.text,
        "recalled_candidate": ADA_KEY in recall,
        "has_citation": "source:" in recall,
        "recall": recall,
    }


def main() -> None:  # pragma: no cover
    """Run the slice: real model + embeddings if a key is set, else the offline fake path.

    EN: Returns: None (prints the recall + the answer). 中文：返回：None（打印召回与答复）。
    """
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    config = CoreConfig.from_env()
    if config.openai_api_key:
        embed_fn = openai_embedder(api_key=config.openai_api_key)
        embed_version = "openai:text-embedding-3-small"
        model = OpenAIProvider(config)
        mode = f"REAL OpenAI ({config.model_id} + text-embedding-3-small)"
    else:
        embed_fn = hashing_embedder(256)
        embed_version = "hash@256"
        model = FakeProvider(script=[ModelResponse(
            text="[offline] Set OPENAI_API_KEY in agent/.env for a real, reasoned shortlist. "
                 "The recall + wiring below still ran.")])
        mode = "OFFLINE / fake model (no OPENAI_API_KEY)"
    print(f"Mode: {mode}\n")
    out = run(QUESTION, embed_fn=embed_fn, embed_version=embed_version, model=model)
    print(f"Q: {QUESTION}\n")
    print(f"Recalled into the prompt (<memory-context>):\n{out['recall']}\n")
    print(f"Agent answer:\n{out['answer']}\n")
    print(f"[recalled the fitting candidate={out['recalled_candidate']}  has_citation={out['has_citation']}]")


if __name__ == "__main__":  # pragma: no cover
    main()
