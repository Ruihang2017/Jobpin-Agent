"""Tests for the §1.4 re-embed migration tool (resumable version switch).

EN — switch hash@64 -> hash@128: full re-embed + validate; resume after an interrupt.
中文 — 切换 hash@64 -> hash@128：完整重嵌入 + 校验；中断后续传。
"""
from jobpin_agent.memory.embedding import embed_version, hashing_embedder
from jobpin_agent.memory.vector.record import VectorRecord
from jobpin_agent.memory.vector.reembed import reembed
from jobpin_agent.memory.vector.store import SqliteVectorStore

E64 = hashing_embedder(64)
E128 = hashing_embedder(128)
V64 = embed_version("hash", 64)
V128 = embed_version("hash", 128)


def _seed():
    """Seed a 3-record source store at hash@64.

    EN: Returns: the source store. 中文：返回：源存储。
    """
    s = SqliteVectorStore()
    s.add([
        VectorRecord("acme:apac:candidate:c1", "hash", V64, "c1", "c1#0", "python distributed", E64("python distributed")),
        VectorRecord("acme:apac:candidate:c2", "hash", V64, "c2", "c2#0", "kubernetes platform", E64("kubernetes platform")),
        VectorRecord("acme:apac:candidate:c3", "hash", V64, "c3", "c3#0", "data engineering", E64("data engineering")),
    ])
    return s


def test_full_reembed_validates():
    """A clean run re-embeds all records into the new version and validates.

    EN: dst has 3 records, all hash@128, validated. 中文：dst 有 3 条全 hash@128，校验通过。
    """
    src = _seed()
    dst = SqliteVectorStore()
    res = reembed(src, dst, E128, V128)
    assert res.complete and res.validated and res.migrated == 3
    assert dst.current_version() == {V128} and len(dst.all_records()) == 3


def test_resume_after_interrupt():
    """An interrupted migration (limit=1) finishes on a re-run, skipping done records.

    EN: first call migrates 1 (incomplete); second migrates the remaining 2 (complete).
    中文：首次迁移 1（未完成）；二次迁移其余 2（完成）。
    """
    src = _seed()
    dst = SqliteVectorStore()
    first = reembed(src, dst, E128, V128, limit=1)
    assert first.migrated == 1 and first.complete is False
    second = reembed(src, dst, E128, V128)
    assert second.migrated == 2 and second.complete and second.validated
    assert len(dst.all_records()) == 3 and dst.current_version() == {V128}
