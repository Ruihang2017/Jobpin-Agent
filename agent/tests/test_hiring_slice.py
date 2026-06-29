"""Tests for the thin hiring vertical slice (real-LLM path opt-in; wiring tested with the fake model).

EN — Deterministic: a fake model + the lexical hashing embedder prove the slice closes end-to-end
(recall + citation + HR/HITL framing reach the model, no loop change). The real-OpenAI test is skipped
without a key (it spends money). 中文 — 确定性：fake 模型 + 词面哈希嵌入器证明切片端到端闭合（召回 + 引用 +
HR/HITL 框定到达模型，不改循环）。真实 OpenAI 测试在无密钥时跳过（会花钱）。
"""
import os
from types import SimpleNamespace

import pytest

from jobpin_agent.core.messages import ModelResponse
from jobpin_agent.core.model.fake_provider import FakeProvider
from jobpin_agent.memory.embedding import hashing_embedder, openai_embedder

from examples.hiring_slice_demo import ADA_KEY, OPENAI_EMBED_VERSION, QUESTION, build_hiring_slice, run

# A query with strong lexical overlap with cand_ada's PROSE, so the fake (lexical) embedder recalls her
# deterministically. (The real semantic embedder handles the looser QUESTION; that's the opt-in test.)
TEST_Q = "who built a globally-distributed payments ledger and mentored engineers?"


def test_slice_recalls_candidate_with_citation_offline():
    """run() recalls the fitting candidate with a source citation (fake model + lexical embedder).

    EN: recalled_candidate + has_citation are True. 中文：recalled_candidate 与 has_citation 均为 True。
    """
    out = run(TEST_Q, embed_fn=hashing_embedder(256), embed_version="hash@256",
              model=FakeProvider(script=[ModelResponse(text="Ada Lovelace looks strongest — suggestion for human review.")]))
    assert out["recalled_candidate"] is True
    assert out["has_citation"] is True


def test_model_sees_hr_framing_and_fenced_recall_offline():
    """The composed prompt the model received carries the HR/HITL framing + the recalled candidate + citation.

    EN: assert against the fake model's recorded call (model.calls[0]); no agent_loop change needed.
    中文：对 fake 模型记录的调用（model.calls[0]）断言；无需改动 agent_loop。
    """
    model = FakeProvider(script=[ModelResponse(text="ok — suggestion for human review")])
    agent, store, sid, manager, hooks = build_hiring_slice(
        embed_fn=hashing_embedder(256), embed_version="hash@256", model=model)
    agent.run_turn(sid, TEST_Q)
    sent = "\n".join(m.content for m in model.calls[0])
    assert "human confirmation" in sent              # HR/HITL framing reached the model
    assert "cand_ada" in sent and "source:" in sent  # the recalled candidate + citation reached the model


def test_openai_embedder_is_lazy_and_injectable():
    """openai_embedder constructs with no key/network and embeds via an injected client.

    EN: callable without a key; a fake client yields its vector. 中文：无密钥即可构造；伪客户端返回其向量。
    """
    assert callable(openai_embedder())  # no key, no network at construction (lazy client)

    class _FakeEmbeddings:
        def create(self, model, input):
            return SimpleNamespace(data=[SimpleNamespace(embedding=[0.1, 0.2, 0.3])])

    embed = openai_embedder(client=SimpleNamespace(embeddings=_FakeEmbeddings()))
    assert embed("hello") == [0.1, 0.2, 0.3]


@pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"),
                    reason="opt-in: needs OPENAI_API_KEY and spends the user's money")
def test_real_openai_hiring_slice():  # pragma: no cover - opt-in, not run in CI
    """With a real key: real embeddings + a real model produce a non-empty shortlist naming a fit.

    EN: the answer is substantial and names a fitting candidate. 中文：答复实质且点名合适候选人。
    """
    from jobpin_agent.core.config import CoreConfig
    from jobpin_agent.core.model.openai_provider import OpenAIProvider

    config = CoreConfig.from_env()
    out = run(QUESTION, embed_fn=openai_embedder(api_key=config.openai_api_key),
              embed_version=OPENAI_EMBED_VERSION, model=OpenAIProvider(config))
    assert out["answer"] and len(out["answer"]) > 20
    assert any(name in out["answer"] for name in ("Ada", "Grace"))
