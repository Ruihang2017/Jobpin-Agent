"""Tests for the §1.4 SemanticRAGProvider (retrieval with source citations).

EN — ingest → NL query recalls the matching chunk with a [source: …] citation; cache path.
中文 — ingest → NL 查询召回匹配片段并带 [source: …] 引用；缓存路径。
"""
from jobpin_agent.memory.embedding import embed_version, hashing_embedder
from jobpin_agent.memory.providers.semantic import SemanticRAGProvider
from jobpin_agent.memory.vector.store import SqliteVectorStore

E = hashing_embedder(64)
VER = embed_version("hash", 64)


def _provider():
    """Build a Semantic provider over a fresh in-memory store.

    EN: Returns: a SemanticRAGProvider at the test embed version.
    中文：返回：测试嵌入版本的 SemanticRAGProvider。
    """
    return SemanticRAGProvider(SqliteVectorStore(), E, embed_model="hash", embed_version=VER, k=2)


def test_ingest_then_recall_with_citation():
    """A query recalls the matching KB chunk with a source citation.

    EN: "structured interview loop" recalls the interview-loop chunk + [source: kb#1].
    中文："structured interview loop" 召回面试环节片段 + [source: kb#1]。
    """
    p = _provider()
    p.ingest("kb", "Always run a structured interview loop with a calibration step.",
             memory_key="acme:apac:semantic:kb", source_ref="kb#1")
    p.ingest("kb", "Reimburse travel within 30 days.", memory_key="acme:apac:semantic:kb", source_ref="kb#2")
    recall = p.prefetch("how do we run a structured interview loop?")
    assert "structured interview loop" in recall and "source: kb#1" in recall
    assert "[memory_key: acme:apac:semantic:kb" in recall


def test_name_and_sync_noop():
    """name is 'semantic' and sync_turn is a no-op.

    EN: name == "semantic"; sync_turn returns None. 中文：name == "semantic"；sync_turn 返回 None。
    """
    p = _provider()
    assert p.name == "semantic" and p.sync_turn("u", "a") is None


def test_queue_then_prefetch_uses_cache():
    """queue_prefetch warms the cache that prefetch returns.

    EN: after queue_prefetch, prefetch returns the warmed result. 中文：queue_prefetch 后，prefetch 返回预热结果。
    """
    p = _provider()
    p.ingest("kb", "calibration meeting agenda", memory_key="acme:apac:semantic:kb", source_ref="kb#1")
    p.queue_prefetch("calibration", session_id="s1")
    assert "calibration" in p.prefetch("calibration", session_id="s1")
