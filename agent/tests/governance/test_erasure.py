"""Tests for ``governance/erasure.py`` — the data-subject erasure drill (exit criterion 2).

EN — Ingest a candidate (recallable) → erase → structured + vector gone, recall cache cleared (re-recall
empty), audit ``erase/ok``, backup-ageing registered. 中文 — ingest 一个候选人（可召回）→ 擦除 → 结构化 + 向量消失、
召回缓存清空（再召回为空）、审计 ``erase/ok``、备份老化已登记。
"""
from jobpin_agent.governance.audit import AuditLog
from jobpin_agent.governance.erasure import Eraser
from jobpin_agent.governance.retention import BackupAgeingRegister
from jobpin_agent.memory.embedding import hashing_embedder
from jobpin_agent.memory.providers.candidate import CandidateMemoryProvider
from jobpin_agent.memory.structured import CandidateRow, CandidateStructuredStore
from jobpin_agent.memory.vector.store import SqliteVectorStore


def test_erasure_cascade_and_cache_clear():
    """erase() removes the live rows+vectors, clears the recall cache, audits, and registers backups.

    EN: the full erasure drill. 中文：完整擦除演练。
    """
    provider = CandidateMemoryProvider(SqliteVectorStore(), CandidateStructuredStore(),
                                       hashing_embedder(256), embed_version="hash@256")
    key = "acme:apac:candidate:x"
    provider.ingest(CandidateRow(key, name="X"), [(key + "#0", "python postgres reliability engineering")])
    assert provider.prefetch("python postgres", session_id="s")   # recalls + caches

    audit, register = AuditLog(), BackupAgeingRegister()
    eraser = Eraser(audit, register, [provider.clear_recall_cache])
    out = eraser.erase(key, actor="dpo:bob", reason="APP 11.2 destruction request",
                       deleter=provider.delete, now_days=0.0, ages_out_at_days=180.0)

    assert out["deleted"]["structured"] == 1 and out["deleted"]["vectors"] == 1
    assert provider.prefetch("python postgres", session_id="s") == ""   # gone + cache cleared
    assert audit.query(action="erase")[-1].result == "ok"
    assert register.pending(10.0) == [key]
