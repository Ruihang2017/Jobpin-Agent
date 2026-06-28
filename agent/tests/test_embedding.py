"""Tests for the §1.4 embedding seam (hashing bag-of-words default).

EN — Deterministic; lexical overlap yields non-zero cosine; vectors are normalised.
中文 — 确定性；词面重叠产生非零余弦；向量已归一化。
"""
import math

from jobpin_agent.memory.embedding import cosine, embed_version, hashing_embedder


def test_lexical_overlap_gives_nonzero_cosine():
    """Shared tokens -> non-zero cosine; disjoint tokens -> ~0.

    EN: "Python engineer" vs "python developer" share "python"; vs "garden leave" disjoint.
    中文："Python engineer" 与 "python developer" 共享 "python"；与 "garden leave" 不相交。
    """
    e = hashing_embedder(64)
    assert cosine(e("Python engineer"), e("python developer")) > 0.0
    assert cosine(e("python"), e("garden leave")) == 0.0


def test_deterministic_and_normalised():
    """Same input -> identical vector; non-empty vectors are L2-normalised.

    EN: e(x)==e(x); ||e(x)||==1 for non-empty; empty -> zero vector.
    中文：e(x)==e(x)；非空时 ||e(x)||==1；空 -> 零向量。
    """
    e = hashing_embedder(64)
    v = e("structured interview loop")
    assert v == e("structured interview loop")
    assert abs(math.sqrt(sum(x * x for x in v)) - 1.0) < 1e-9
    assert e("") == [0.0] * 64


def test_embed_version_signature():
    """embed_version is name@dim.

    EN: ("hash", 64) -> "hash@64". 中文：("hash", 64) -> "hash@64"。
    """
    assert embed_version("hash", 64) == "hash@64"
