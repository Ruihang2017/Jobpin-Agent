"""Tests for the §1.4 CandidateMemoryProvider (gated ingest, filter-before-NN, cascade).

EN — ingest a candidate; recall with citation; scope_filter excludes -> ""; delete cascades;
write_gate holds an ingest. 中文 — ingest 候选人；带引用召回；scope_filter 排除 -> ""；delete 级联；
write_gate 保留 ingest。
"""
from jobpin_agent.memory.embedding import embed_version, hashing_embedder
from jobpin_agent.memory.providers.candidate import CandidateMemoryProvider
from jobpin_agent.memory.structured import CandidateRow, CandidateStructuredStore
from jobpin_agent.memory.vector.store import SqliteVectorStore

E = hashing_embedder(64)
VER = embed_version("hash", 64)
KEY = "acme:apac:candidate:cand_7f3a"


def _provider(scope_filter=None, write_gate=None):
    """Build a Candidate provider over fresh stores.

    EN: Args: scope_filter; write_gate. Returns: a CandidateMemoryProvider.
    中文：参数：scope_filter；write_gate。返回：CandidateMemoryProvider。
    """
    return CandidateMemoryProvider(
        SqliteVectorStore(), CandidateStructuredStore(), E,
        embed_model="hash", embed_version=VER, scope_filter=scope_filter, write_gate=write_gate, k=3,
    )


def _ingest(p):
    """Ingest one python candidate with two résumé chunks.

    EN: Args: p. Returns: None. 中文：参数：p。返回：None。
    """
    p.ingest(
        CandidateRow(KEY, name="Ada", skills=["python", "distributed"], years=6, work_rights=True),
        [(f"{KEY}#0", "Senior Python engineer building distributed systems."),
         (f"{KEY}#1", "Led Kubernetes migration.")],
    )


def test_ingest_then_recall_with_citation():
    """A query recalls the candidate with a citation to the key + chunk.

    EN: recall contains the candidate memory_key and a source_ref. 中文：召回含候选人 memory_key 与 source_ref。
    """
    p = _provider()
    _ingest(p)
    recall = p.prefetch("python distributed systems")
    assert KEY in recall and f"{KEY}#0" in recall


def test_scope_filter_excludes_candidate():
    """A scope_filter that excludes the candidate yields no recall (filter before NN).

    EN: scope_filter -> False for KEY -> "". 中文：scope_filter 对 KEY 返回 False -> ""。
    """
    p = _provider(scope_filter=lambda mk: mk != KEY)
    _ingest(p)
    assert p.prefetch("python") == ""


def test_delete_cascades_structured_and_vectors():
    """delete removes the structured row and the derived vectors.

    EN: after delete, recall is empty and counts are returned. 中文：delete 后召回为空且返回计数。
    """
    p = _provider()
    _ingest(p)
    counts = p.delete(KEY)
    assert counts["structured"] == 1 and counts["vectors"] == 2
    assert p.prefetch("python") == ""


def test_write_gate_holds_ingest():
    """A write_gate that returns a message holds the ingest (nothing persisted).

    EN: gate -> staged; recall stays empty. 中文：门控 -> 暂存；召回保持为空。
    """
    p = _provider(write_gate=lambda action, target, key: "needs consent label")
    r = p.ingest(CandidateRow(KEY, skills=["python"]), [(f"{KEY}#0", "python")])
    assert r["success"] is False and r["staged"] is True
    assert p.prefetch("python") == ""
