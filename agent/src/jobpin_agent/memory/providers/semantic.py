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

from typing import Any, Callable, Dict, List, Optional

from ...security.threat_patterns import first_threat_message
from ..embedding import EmbedFn
from ..vector.record import VectorRecord
from ..vector.rerank import RerankFn
from ..vector.store import VectorStore
from .retrieval_base import Hit, RetrievalProvider


def _default_scan(text: str):
    """Fail-safe default scan for KB-doc ingest (§1.6) — the context-scope threat scan.

    EN: Args: text (a knowledge-base chunk). Returns: a threat description or None. KB content can be
        untrusted (scraped/imported), so the semantic sink scans by default; pass a callable to override.
    中文：参数：text（知识库片段）。返回：威胁描述或 None。KB 内容可能不可信（抓取/导入），故语义汇默认扫描；传入以覆盖。
    """
    return first_threat_message(text, "context")


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
        write_gate: Optional[Callable[[str, str, str], Optional[str]]] = None,
        scan_entry: Optional[Callable[[str], Optional[str]]] = None,
        rerank: Optional[RerankFn] = None,
        k: int = 4,
    ) -> None:
        """Construct the provider.

        EN: Args: see the class docstring; write_gate (ingest approval, default pass-through — §1.5);
            scan_entry (threat scan on ingested text — **defaults to the §1.6 context-scope threat scan**;
            pass an explicit callable to override/disable); rerank (default identity).
        中文：参数：见类文档；write_gate（ingest 审批，默认直通——§1.5）；scan_entry（ingest 文本威胁扫描，**默认采用
            §1.6 context 范围威胁扫描**；传入显式可调用对象以覆盖/禁用）；rerank（默认恒等）。
        """
        super().__init__(rerank=rerank)
        self._store = vector_store
        self._embed = embed_fn
        self._embed_model = embed_model
        self._embed_version = embed_version
        self._scope = scope_filter or (lambda _mk: True)
        self._gate = write_gate
        self._scan = scan_entry if scan_entry is not None else _default_scan
        self._k = k

    @property
    def name(self) -> str:
        """Provider name.

        EN: Returns: "semantic". 中文：返回："semantic"。
        """
        return "semantic"

    def ingest(self, doc_id: str, text: str, *, memory_key: str, source_ref: str) -> Dict[str, Any]:
        """Embed and store one knowledge-base chunk (through the scan + gate seams).

        EN —
        Args: doc_id (struct_ref); text; memory_key; source_ref (citation pointer). Returns: a success
        dict, or ``{"blocked": …}`` if ``scan_entry`` flags the text (§1.6), or a staged dict if
        ``write_gate`` holds the write (§1.5). Both seams are pass-through by default.
        中文 —
        参数：doc_id（struct_ref）；text；memory_key；source_ref（引用指针）。返回：成功字典，或若 ``scan_entry``
        标记文本（§1.6）则 ``{"blocked": …}``，或若 ``write_gate`` 保留写入（§1.5）则暂存字典。两接缝默认直通。
        """
        if self._scan is not None:
            desc = self._scan(text)
            if desc:
                return {"success": False, "blocked": desc}
        if self._gate is not None:
            held = self._gate("add", "semantic", memory_key)
            if held:
                return {"success": False, "staged": True, "message": held}
        self._store.add([VectorRecord(
            memory_key=memory_key, embed_model=self._embed_model, embed_version=self._embed_version,
            struct_ref=doc_id, source_ref=source_ref, text=text, embedding=self._embed(text),
        )])
        return {"success": True, "ingested": 1}

    def _retrieve(self, query: str, session_id: str) -> List[Hit]:
        """Embed the query and search with the scope predicate applied BEFORE the top-k truncation.

        EN: Args: query; session_id. Returns: scoped top-k hits (no retrieve-then-filter leak).
        中文：参数：query；session_id。返回：经范围限定的 top-k 命中（无先检索后过滤泄漏）。
        """
        return self._store.search(self._embed(query), self._k, scope=self._scope)
