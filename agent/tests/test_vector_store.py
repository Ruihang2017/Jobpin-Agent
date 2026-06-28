"""Tests for the §1.4 vector store (cosine NN, key-prefix cascade, drift guard).

EN — Ranking by cosine; key_prefix pre-filter; delete_by_key_prefix erasure cascade;
the single-embed_version drift guard. 中文 — 余弦排序；key_prefix 预过滤；delete_by_key_prefix
擦除级联；单 embed_version 漂移守卫。
"""
import pytest

from jobpin_agent.memory.embedding import embed_version, hashing_embedder
from jobpin_agent.memory.vector.record import VectorRecord
from jobpin_agent.memory.vector.store import SqliteVectorStore

E = hashing_embedder(64)
VER = embed_version("hash", 64)


def _rec(memory_key, source_ref, text):
    """Build a VectorRecord for the test embedder.

    EN: Args: memory_key, source_ref, text. Returns: a VectorRecord at VER.
    中文：参数：memory_key、source_ref、text。返回：VER 版本的 VectorRecord。
    """
    return VectorRecord(
        memory_key=memory_key, embed_model="hash", embed_version=VER,
        struct_ref=memory_key, source_ref=source_ref, text=text, embedding=E(text),
    )


def test_search_ranks_by_cosine():
    """The chunk sharing query tokens ranks first.

    EN: query "python distributed systems" -> the python chunk first.
    中文：查询 "python distributed systems" -> python 片段最前。
    """
    s = SqliteVectorStore()
    s.add([
        _rec("acme:apac:candidate:cand_1", "cand_1#0", "Senior Python engineer, distributed systems."),
        _rec("acme:apac:candidate:cand_2", "cand_2#0", "Landscape gardener, horticulture diploma."),
    ])
    hits = s.search(E("python distributed systems"), k=2)
    assert hits and hits[0][0].memory_key == "acme:apac:candidate:cand_1"


def test_key_prefix_pre_filters():
    """key_prefix restricts search to one subject (filter before NN).

    EN: scoping to cand_1 never returns cand_2. 中文：限定 cand_1 绝不返回 cand_2。
    """
    s = SqliteVectorStore()
    s.add([
        _rec("acme:apac:candidate:cand_1", "cand_1#0", "python developer"),
        _rec("acme:apac:candidate:cand_2", "cand_2#0", "python developer"),
    ])
    hits = s.search(E("python"), k=5, key_prefix="acme:apac:candidate:cand_1")
    assert all(h[0].memory_key == "acme:apac:candidate:cand_1" for h in hits)


def test_delete_by_key_prefix_cascade():
    """delete_by_key_prefix removes a subject's vectors and returns the count.

    EN: erasing cand_1 deletes its rows; cand_2 remains. 中文：擦除 cand_1 删其行；cand_2 留存。
    """
    s = SqliteVectorStore()
    s.add([
        _rec("acme:apac:candidate:cand_1", "cand_1#0", "python"),
        _rec("acme:apac:candidate:cand_1", "cand_1#1", "kubernetes"),
        _rec("acme:apac:candidate:cand_2", "cand_2#0", "python"),
    ])
    removed = s.delete_by_key_prefix("acme:apac:candidate:cand_1")
    assert removed == 2
    assert all(h[0].memory_key == "acme:apac:candidate:cand_2" for h in s.search(E("python"), k=5))


def test_drift_guard_rejects_foreign_version():
    """A record from a different vector space is rejected (no silent mixing).

    EN: store pinned at hash@64; adding a hash@128 record -> ValueError.
    中文：存储固定 hash@64；加入 hash@128 记录 -> ValueError。
    """
    s = SqliteVectorStore()
    s.add([_rec("acme:apac:candidate:cand_1", "cand_1#0", "python")])
    assert s.current_version() == {VER}
    foreign = VectorRecord(
        memory_key="acme:apac:candidate:cand_3", embed_model="hash", embed_version="hash@128",
        struct_ref="x", source_ref="x#0", text="python", embedding=hashing_embedder(128)("python"),
    )
    with pytest.raises(ValueError):
        s.add([foreign])
