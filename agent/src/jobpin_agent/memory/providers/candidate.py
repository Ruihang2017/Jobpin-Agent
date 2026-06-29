"""CandidateMemoryProvider (§1.4) — candidate profiles: structured fields + résumé vectors.

EN —
Pairs a candidate's structured row (skills / years / location / work rights / consent) with the
semantic vectors of their résumé chunks. ``ingest`` writes both — through an injected ``write_gate``
(pass-through in §1.4; the real governance gate that rejects unlabelled writes is §1.5). ``prefetch``
**filters before nearest-neighbour**: it narrows to the candidates allowed by ``scope_filter``
(RBAC/namespace) FIRST, then runs vector NN only over those — closing the "retrieve first, filter
later" leak of an unauthorised candidate's very existence (Plan §1.4 / §1.5). ``delete`` cascades:
structured row + derived vectors by ``memory_key`` prefix (the §1.5 erasure mechanism).

中文 —
把候选人的结构化行（技能 / 年限 / 地点 / 工作权利 / 同意）与其简历片段的语义向量配对。``ingest`` 同时写入两者——
经注入的 ``write_gate``（§1.4 直通；拒绝未标注写入的真实治理门控是 §1.5）。``prefetch`` **先过滤再近邻**：先按
``scope_filter``（RBAC/命名空间）收窄到允许的候选人，再仅对其做向量近邻——堵住“先检索后过滤”泄漏未授权候选人存在性
（计划 §1.4 / §1.5）。``delete`` 级联：结构化行 + 按 ``memory_key`` 前缀的派生向量（§1.5 擦除机制）。
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from ...security.threat_patterns import first_threat_message
from ..embedding import EmbedFn
from ..structured import CandidateRow, CandidateStructuredStore
from ..vector.record import VectorRecord
from ..vector.rerank import RerankFn
from ..vector.store import VectorStore
from .retrieval_base import Hit, RetrievalProvider


def _default_scan(text: str):
    """Fail-safe default chunk scan for candidate ingest (§1.6) — the context-scope threat scan.

    EN: Args: text (a résumé chunk). Returns: a threat description or None. Résumé text is untrusted
        (prompt-injection via résumé), so the candidate memory sink scans by default; override to disable.
    中文：参数：text（简历片段）。返回：威胁描述或 None。简历文本不可信（经简历的提示注入），故候选人记忆汇默认扫描；
        传入以禁用。
    """
    return first_threat_message(text, "context")


class CandidateMemoryProvider(RetrievalProvider):
    """Candidate entity memory over a vector + structured store (name ``"candidate"``).

    EN —
    Args (constructor): vector_store; structured_store; embed_fn; embed_model / embed_version;
    scope_filter (RBAC predicate on memory_key, default open); write_gate (ingest approval, default
    pass-through); k.

    中文 —
    参数（构造）：vector_store；structured_store；embed_fn；embed_model / embed_version；scope_filter
    （memory_key 的 RBAC 谓词，默认放行）；write_gate（ingest 审批，默认直通）；k。
    """

    entity_type = "candidate"

    def __init__(
        self,
        vector_store: VectorStore,
        structured_store: CandidateStructuredStore,
        embed_fn: EmbedFn,
        *,
        embed_model: str = "hash",
        embed_version: str = "hash@256",
        scope_filter: Optional[Callable[[str], bool]] = None,
        write_gate: Optional[Callable[[str, str, str], Optional[str]]] = None,
        scan_entry: Optional[Callable[[str], Optional[str]]] = None,
        governance: Optional[Any] = None,
        actor: str = "system",
        rerank: Optional[RerankFn] = None,
        k: int = 4,
    ) -> None:
        """Construct the provider.

        EN: Args: see the class docstring; scan_entry (threat scan on ingested chunk text — flagged chunks
            are skipped; **defaults to the §1.6 context-scope threat scan** since résumé text is untrusted,
            pass an explicit callable to override/disable); governance (an optional
            §1.5 ``GovernanceGate`` — when set, ``ingest`` enforces provenance + granted consent and
            rejects unlabelled/unconsented candidate writes; default None preserves §1.4 behaviour);
            actor (audit actor for the governance check); rerank (default identity).
        中文：参数：见类文档；scan_entry（ingest 片段文本威胁扫描，默认直通——被标记的片段跳过；真实扫描器为 §1.6）；
            governance（可选的 §1.5 ``GovernanceGate``——设置后 ``ingest`` 强制来源 + 已授予同意，拒绝未标注/未同意的
            候选人写入；默认 None 保留 §1.4 行为）；actor（治理检查的审计执行者）；rerank（默认恒等）。
        """
        super().__init__(rerank=rerank)
        self._vec = vector_store
        self._struct = structured_store
        self._embed = embed_fn
        self._embed_model = embed_model
        self._embed_version = embed_version
        self._scope = scope_filter or (lambda _mk: True)
        self._gate = write_gate
        self._scan = scan_entry if scan_entry is not None else _default_scan
        self._governance = governance
        self._actor = actor
        self._k = k

    @property
    def name(self) -> str:
        """Provider name.

        EN: Returns: "candidate". 中文：返回："candidate"。
        """
        return "candidate"

    def ingest(self, candidate: CandidateRow, chunks: List[Tuple[str, str]]) -> Dict[str, Any]:
        """Write the candidate's structured row + résumé-chunk vectors (gated).

        EN —
        Args: candidate (structured row); chunks (list of ``(source_ref, text)``). Returns: a success
        dict, or a staged dict if the ``write_gate`` holds the write (nothing persisted).
        中文 —
        参数：candidate（结构化行）；chunks（``(source_ref, text)`` 列表）。返回：成功字典；若 §1.5 治理拒绝则为
        ``{"success": False, "rejected": <码>}``；或若 ``write_gate`` 保留写入则为暂存字典（不持久化）。
        """
        if self._governance is not None:
            decision = self._governance.validate_entity_ingest(
                candidate.memory_key, candidate.consent_status, [sr for sr, _ in chunks], actor=self._actor)
            if not decision.ok:
                return {"success": False, "rejected": decision.code.split(":", 1)[-1], "code": decision.code}
        if self._gate is not None:
            held = self._gate("add", "candidate", candidate.memory_key)
            if held:
                return {"success": False, "staged": True, "message": held}
        clean = [(sr, t) for sr, t in chunks if not (self._scan is not None and self._scan(t))]
        self._struct.upsert(candidate)
        records = [VectorRecord(
            memory_key=candidate.memory_key, embed_model=self._embed_model, embed_version=self._embed_version,
            struct_ref=candidate.memory_key, source_ref=source_ref, text=text, embedding=self._embed(text),
        ) for source_ref, text in clean]
        if records:
            self._vec.add(records)
        return {"success": True, "ingested": len(records), "skipped": len(chunks) - len(records)}

    def delete(self, memory_key: str) -> Dict[str, int]:
        """Erase a candidate: structured row + derived vectors (the §1.5 cascade mechanism).

        EN: Args: memory_key. Returns: ``{"structured": n, "vectors": m}`` removed.
        中文：参数：memory_key。返回：删除的 ``{"structured": n, "vectors": m}``。
        """
        return {
            "structured": self._struct.delete_by_key_prefix(memory_key),
            "vectors": self._vec.delete_by_key_prefix(memory_key),
        }

    def _retrieve(self, query: str, session_id: str) -> List[Hit]:
        """Filter to the authorised candidates FIRST, then vector NN over only those (one search).

        EN —
        Args: query; session_id. Returns: scoped top-k hits (empty if nothing authorised). The
        structured store yields the allowed ``memory_key`` set (RBAC), passed to ``search`` as a
        ``scope`` predicate so filtering happens BEFORE the top-k truncation in a single search.
        中文 —
        参数：query；session_id。返回：经范围限定的 top-k 命中（无授权则为空）。结构化库产出允许的 ``memory_key``
        集合（RBAC），作为 ``scope`` 谓词传给 ``search``，使过滤在单次搜索中于 top-k 截断**之前**发生。
        """
        allowed = {r.memory_key for r in self._struct.filter(lambda r: self._scope(r.memory_key))}
        if not allowed:
            return []
        return self._vec.search(self._embed(query), self._k, scope=lambda mk: mk in allowed)
