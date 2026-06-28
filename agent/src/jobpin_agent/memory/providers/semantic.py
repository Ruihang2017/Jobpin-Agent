"""SemanticRAGProvider (§1.4) — the knowledge-base semantic retrieval layer.

EN —
A read-mostly RAG index over knowledge-base / semantic chunks (interview playbooks, JDs,
policy text). ``ingest`` embeds + stores a chunk; ``prefetch`` retrieves the nearest chunks for a
query and returns them as fenced, citation-bearing recall. ``sync_turn`` is a no-op — knowledge-base
updates are explicit ``ingest`` calls, not per-turn writes. The real semantic embedder (BGE/OpenAI)
plugs in behind the injected ``EmbedFn``; §1.4 ships the lexical hashing default.

中文 —
对知识库 / 语义片段（面试手册、JD、政策文本）的以读为主的 RAG 索引。``ingest`` 嵌入并存储一个片段；``prefetch``
为查询检索最近片段并以围栏、带引用的召回返回。``sync_turn`` 为空操作——知识库更新是显式 ``ingest`` 调用，而非每回合写入。
真实语义嵌入器（BGE/OpenAI）经注入的 ``EmbedFn`` 接入；§1.4 交付词面哈希默认。
"""
from __future__ import annotations

from typing import Callable, List, Optional

from ..embedding import EmbedFn
from ..vector.record import VectorRecord
from ..vector.store import VectorStore
from .retrieval_base import Hit, RetrievalProvider


class SemanticRAGProvider(RetrievalProvider):
    """A semantic RAG provider over a vector store (name ``"semantic"``).

    EN —
    Args (constructor): vector_store; embed_fn; embed_model / embed_version (pinned signature for
    stored records); scope_filter (namespace/RBAC predicate on memory_key, default open); k.

    中文 —
    参数（构造）：vector_store；embed_fn；embed_model / embed_version（存储记录的固定签名）；scope_filter
    （memory_key 的命名空间/RBAC 谓词，默认放行）；k。
    """

    entity_type = "semantic"

    def __init__(
        self,
        vector_store: VectorStore,
        embed_fn: EmbedFn,
        *,
        embed_model: str = "hash",
        embed_version: str = "hash@256",
        scope_filter: Optional[Callable[[str], bool]] = None,
        k: int = 4,
    ) -> None:
        """Construct the provider.

        EN: Args: see the class docstring. 中文：参数：见类文档。
        """
        super().__init__()
        self._store = vector_store
        self._embed = embed_fn
        self._embed_model = embed_model
        self._embed_version = embed_version
        self._scope = scope_filter or (lambda _mk: True)
        self._k = k

    @property
    def name(self) -> str:
        """Provider name.

        EN: Returns: "semantic". 中文：返回："semantic"。
        """
        return "semantic"

    def ingest(self, doc_id: str, text: str, *, memory_key: str, source_ref: str) -> None:
        """Embed and store one knowledge-base chunk.

        EN: Args: doc_id (struct_ref); text; memory_key; source_ref (citation pointer). Returns: None.
        中文：参数：doc_id（struct_ref）；text；memory_key；source_ref（引用指针）。返回：None。
        """
        self._store.add([VectorRecord(
            memory_key=memory_key, embed_model=self._embed_model, embed_version=self._embed_version,
            struct_ref=doc_id, source_ref=source_ref, text=text, embedding=self._embed(text),
        )])

    def _retrieve(self, query: str, session_id: str) -> List[Hit]:
        """Embed the query, search, and drop hits outside the authorised scope.

        EN: Args: query; session_id. Returns: scoped top-k hits.
        中文：参数：query；session_id。返回：经范围限定的 top-k 命中。
        """
        qv = self._embed(query)
        hits = self._store.search(qv, self._k)
        return [(rec, score) for rec, score in hits if self._scope(rec.memory_key)]
