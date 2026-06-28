"""The embedding seam — inject the embedder; default is dependency-free (§1.4).

EN —
``EmbedFn`` is the contract the retrieval providers (§1.4) call to turn text into a
vector. The default ``hashing_embedder`` is a deterministic, stdlib-only **hashing
bag-of-words** vectoriser: it tokenises, hashes each token into a fixed-width vector,
counts, and L2-normalises. It captures **lexical overlap** (so "Python engineer" and
"python developer" share the "python" dimension and have non-zero cosine) — enough to
exercise the retrieval pipeline + tests offline, with no heavy dependency.

A real **semantic** embedder (BGE via sentence-transformers, or OpenAI
``text-embedding-3``) plugs in behind the same ``EmbedFn`` type via config — and a model
swap (a new ``embed_version``) triggers the §1.4 re-embed migration. The fake embedder is
NOT a quality or security control; it only proves the plumbing.

中文 —
``EmbedFn`` 是检索 provider（§1.4）将文本转为向量所调用的契约。默认 ``hashing_embedder`` 是一个确定性、仅用标准库的
**哈希词袋**向量化器：分词、把每个 token 哈希进定宽向量、计数、L2 归一化。它捕获**词面重叠**（故 "Python engineer"
与 "python developer" 共享 "python" 维度、余弦非零）——足以离线演练检索流水线与测试，且无重依赖。

真实**语义**嵌入器（经 sentence-transformers 的 BGE，或 OpenAI ``text-embedding-3``）经配置在同一 ``EmbedFn`` 类型
背后接入——模型切换（新的 ``embed_version``）触发 §1.4 重嵌入迁移。fake 嵌入器并非质量或安全控制，仅证明管路。
"""
from __future__ import annotations

import hashlib
import math
import re
from typing import Callable, List

# The injectable embedder contract: text -> a (normalised) vector.
EmbedFn = Callable[[str], List[float]]

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> List[str]:
    """Lowercase-tokenise into alphanumeric runs.

    EN: Args: text. Returns: a list of lowercase tokens.
    中文：参数：text。返回：小写 token 列表。
    """
    return _TOKEN_RE.findall(text.lower())


def cosine(a: List[float], b: List[float]) -> float:
    """Cosine similarity of two equal-length vectors (0.0 if either is zero).

    EN: Args: a, b (same length). Returns: dot(a,b) / (|a||b|), or 0.0 if a norm is 0.
    中文：参数：a、b（等长）。返回：dot(a,b) / (|a||b|)，任一模为 0 则返回 0.0。
    """
    if len(a) != len(b):
        raise ValueError(f"cosine: vector length mismatch {len(a)} != {len(b)} (embedder/store dim drift)")
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def hashing_embedder(dim: int = 256) -> EmbedFn:
    """Build a deterministic hashing bag-of-words embedder (the §1.4 default).

    EN —
    Each token is hashed (BLAKE2b) into one of ``dim`` buckets and counted; the vector is
    L2-normalised (empty text -> a zero vector). Deterministic across runs/processes, so
    tests and the recall demo are reproducible. Captures lexical overlap, not semantics.
    Args: dim — vector width. Returns: an ``EmbedFn``.

    中文 —
    每个 token 经 BLAKE2b 哈希进 ``dim`` 个桶之一并计数；向量做 L2 归一化（空文本 -> 零向量）。跨运行/进程确定，
    故测试与召回演示可复现。捕获词面重叠，而非语义。参数：dim——向量宽度。返回：一个 ``EmbedFn``。
    """

    def embed(text: str) -> List[float]:
        """Embed one string into a normalised ``dim``-vector.

        EN: Args: text. Returns: an L2-normalised list of ``dim`` floats.
        中文：参数：text。返回：L2 归一化的 ``dim`` 维浮点列表。
        """
        vec = [0.0] * dim
        for tok in _tokenize(text):
            h = int(hashlib.blake2b(tok.encode("utf-8"), digest_size=8).hexdigest(), 16)
            vec[h % dim] += 1.0
        norm = math.sqrt(sum(x * x for x in vec))
        if norm == 0.0:
            return vec
        return [x / norm for x in vec]

    return embed


def embed_version(name: str, dim: int) -> str:
    """Build the pinned embed-version signature (name + dimension).

    EN —
    Recorded alongside every vector. A mismatch means the vector space is incompatible and
    a re-embed migration is required (no silent mixing). Args: name; dim. Returns: ``"name@dim"``.

    中文 —
    与每个向量一同记录。不一致意味着向量空间不兼容、需重嵌入迁移（不静默混用）。参数：name；dim。返回：``"name@dim"``。
    """
    return f"{name}@{dim}"
