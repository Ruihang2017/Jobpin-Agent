"""Test for the §1.4 recall + P95 benchmark scaffold.

EN — recall@k in [0,1], p95_ms a float, n == len(queries). 中文 — recall@k 属 [0,1]，p95_ms 为浮点，n == 查询数。
"""
from jobpin_agent.memory.benchmark import run_recall_benchmark
from jobpin_agent.memory.embedding import embed_version, hashing_embedder
from jobpin_agent.memory.providers.candidate import CandidateMemoryProvider
from jobpin_agent.memory.structured import CandidateRow, CandidateStructuredStore
from jobpin_agent.memory.vector.store import SqliteVectorStore

E = hashing_embedder(64)
VER = embed_version("hash", 64)


def test_benchmark_reports_recall_and_p95():
    """The benchmark returns recall@k, p95_ms, and n over labelled queries.

    EN: a python query finds the python candidate -> recall_at_k > 0; p95_ms >= 0.
    中文：python 查询找到 python 候选人 -> recall_at_k > 0；p95_ms >= 0。
    """
    p = CandidateMemoryProvider(SqliteVectorStore(), CandidateStructuredStore(), E,
                                embed_model="hash", embed_version=VER, k=3)
    p.ingest(CandidateRow("acme:apac:candidate:c1", skills=["python"]), [("c1#0", "python distributed systems")])
    p.ingest(CandidateRow("acme:apac:candidate:c2", skills=["go"]), [("c2#0", "golang microservices")])
    out = run_recall_benchmark(p, [
        ("python distributed", "acme:apac:candidate:c1"),
        ("golang microservices", "acme:apac:candidate:c2"),
    ], k=3)
    assert out["n"] == 2 and 0.0 <= out["recall_at_k"] <= 1.0 and out["recall_at_k"] > 0.0
    assert isinstance(out["p95_ms"], float) and out["p95_ms"] >= 0.0
