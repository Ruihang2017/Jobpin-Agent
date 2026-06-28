"""Shared base for retrieval providers (§1.4) — fast, cached, citation-bearing prefetch.

EN —
The entity providers (Semantic, Candidate) share one shape: ``prefetch`` = embed the query →
nearest-neighbour → render fenced text **with a provenance citation**, and it must be FAST.
Following Hermes's design, the heavy work is done in ``queue_prefetch`` (the §1.3 background
warm-up) and cached by ``(query, session_id)``; ``prefetch`` returns the cache, falling back to a
synchronous compute when cold (bounded — fine at the local scale). Subclasses implement
``_retrieve`` (the actual NN, including any filter-before-NN scoping); the base renders + caches.

中文 —
实体 provider（Semantic、Candidate）共享同一形态：``prefetch`` = 嵌入查询 → 近邻 → 渲染带**来源引用**的围栏文本，
且必须快。沿用 Hermes 设计，重活在 ``queue_prefetch``（§1.3 后台预热）完成并按 ``(query, session_id)`` 缓存；
``prefetch`` 返回缓存，冷时回退到同步计算（有界——在本地规模下足够）。子类实现 ``_retrieve``（真实近邻，含任何
先过滤再近邻的范围限定）；基类负责渲染 + 缓存。
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ..provider import MemoryProvider
from ..store import ENTRY_DELIMITER
from ..vector.rerank import RerankFn, identity_rerank
from ..vector.store import Hit


class RetrievalProvider(MemoryProvider):
    """Base for vector-retrieval providers (caches + reranks + renders; subclass implements ``_retrieve``).

    EN —
    Implements the §1.3 ``MemoryProvider`` lifecycle for retrieval: ``prefetch`` (cache-or-compute),
    ``queue_prefetch`` (warm the cache), an injected ``rerank`` step (default identity), and a citation
    renderer. ``name`` stays abstract.

    中文 —
    为检索实现 §1.3 ``MemoryProvider`` 生命周期：``prefetch``（缓存或计算）、``queue_prefetch``（预热缓存）、注入的
    ``rerank`` 步骤（默认恒等）与引用渲染。``name`` 仍为抽象。
    """

    def __init__(self, *, rerank: Optional[RerankFn] = None) -> None:
        """Initialise the per-(query,session) recall cache and the rerank seam.

        EN: Args: rerank (default ``identity_rerank`` — keep cosine order). Returns: None.
        中文：参数：rerank（默认 ``identity_rerank``——保持余弦顺序）。返回：None。
        """
        self._cache: Dict[Tuple[str, str], str] = {}
        self._rerank: RerankFn = rerank or identity_rerank

    def is_available(self) -> bool:
        """Local retrieval is always available.

        EN: Returns: True. 中文：返回：True。
        """
        return True

    def initialize(self, session_id: str, **kwargs) -> None:
        """No-op (the stores are constructed by the composition root).

        EN: Args: session_id, kwargs (ignored). 中文：参数：session_id、kwargs（忽略）。
        """
        return None

    def get_tool_schemas(self) -> List[dict]:
        """No model-facing tools in §1.4 (retrieval is automatic via prefetch).

        EN: Returns: []. 中文：返回：[]。
        """
        return []

    def _retrieve(self, query: str, session_id: str) -> List[Hit]:
        """Return scored records for a query (subclass implements the NN + scoping).

        EN: Args: query; session_id. Returns: hits, score-desc.
        中文：参数：query；session_id。返回：按分数降序的命中。
        """
        raise NotImplementedError

    def _render(self, hits: List[Hit]) -> str:
        """Render hits as ENTRY_DELIMITER-joined entries, each with a provenance citation.

        EN —
        One entry per hit: ``<text>\\n[memory_key: <key> | source: <source_ref>]`` — the "back to
        source" citation (the namespace key + the original chunk pointer). Joined by
        ``ENTRY_DELIMITER`` so the Composite can split + dedup. Empty hits -> "".
        Args: hits. Returns: the recall text.

        中文 —
        每个命中一条：``<text>\\n[memory_key: <键> | source: <source_ref>]``——“回到来源”引用（命名空间键 + 原片段
        指针）。以 ``ENTRY_DELIMITER`` 连接，使 Composite 可切分 + 去重。无命中 -> ""。参数：hits。返回：召回文本。
        """
        entries = [
            f"{rec.text}\n[memory_key: {rec.memory_key} | source: {rec.source_ref}]"
            for rec, _score in hits
        ]
        return ENTRY_DELIMITER.join(entries)

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        """Return cached recall, computing synchronously when cold.

        EN: Args: query; session_id. Returns: the rendered recall (or "").
        中文：参数：query；session_id。返回：渲染后的召回（或 ""）。
        """
        key = (query, session_id)
        if key in self._cache:
            return self._cache[key]
        result = self._render(self._rerank(query, self._retrieve(query, session_id)))
        self._cache[key] = result
        return result

    def queue_prefetch(self, query: str, *, session_id: str = "") -> None:
        """Warm the cache for the next turn (runs on the §1.3 background worker).

        EN: Args: query; session_id. Returns: None.
        中文：参数：query；session_id。返回：None。
        """
        self._cache[(query, session_id)] = self._render(self._rerank(query, self._retrieve(query, session_id)))
