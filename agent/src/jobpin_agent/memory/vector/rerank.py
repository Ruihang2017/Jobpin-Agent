"""The rerank seam (§1.4) — reorder nearest-neighbour hits before they are rendered.

EN —
Nearest-neighbour gives a *first-pass* ordering by vector similarity; a **reranker** can refine it
(e.g. a cross-encoder, or a BM25 + dense hybrid as in PRD §11.3). §1.4 ships the **interface** + an
``identity_rerank`` default (keep the cosine order); a real reranker plugs in behind ``RerankFn`` —
the §1.12 spike / Phase-1 quality line decides which. Like ``EmbedFn`` / ``scope_filter`` / ``write_gate``,
it is an injected, default-safe seam, so the retrieval providers don't change when it lands.

中文 —
近邻给出按向量相似度的*初排*；**重排器**可对其精炼（如交叉编码器，或 PRD §11.3 的 BM25 + dense 混合）。§1.4 交付
**接口** + ``identity_rerank`` 默认（保持余弦顺序）；真实重排器经 ``RerankFn`` 接入——由 §1.12 spike / Phase-1 质量线
决定。与 ``EmbedFn`` / ``scope_filter`` / ``write_gate`` 一样，它是注入式、默认安全的接缝，故落地时检索 provider 不变。
"""
from __future__ import annotations

from typing import Callable, List

from .store import Hit

# Reorder hits for a query; must return a (sub)list of the given hits.
RerankFn = Callable[[str, List[Hit]], List[Hit]]


def identity_rerank(query: str, hits: List[Hit]) -> List[Hit]:
    """The default reranker — keep the nearest-neighbour (cosine) order unchanged.

    EN: Args: query (ignored); hits. Returns: ``hits`` unchanged. 中文：参数：query（忽略）；hits。返回：原样 ``hits``。
    """
    return hits
