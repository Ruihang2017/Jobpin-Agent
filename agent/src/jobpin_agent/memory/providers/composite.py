"""Minimal CompositeMemoryProvider (§1.4) — the sole external facade over several sub-providers.

EN —
§1.4 lands two coexisting retrieval providers (Candidate + Semantic), which would trip the §1.3
Manager's "one external provider" rule. Rather than relax that rule, the Composite is registered as
the **single** external provider (the builtin curated store stays first) and holds the sub-providers
internally: ``prefetch`` broadcasts and **merges** (split on ``ENTRY_DELIMITER`` → order-preserving
``dict.fromkeys`` dedup → budget-truncate); the lifecycle hooks fan out; ``shutdown`` runs in reverse.
``sync_turn`` **unicasts** to the owning sub-provider when an ``entity_type`` is supplied, else fans out.
This reuses — and never breaks — the §1.3 single-worker / ``flush_pending`` / bounded-drain invariants
(it runs inside them). The full Composite (Employee sub-provider, the entity_type + query-intent routing
table, merge-consistency hardening, backup aggregation) is Phase 2 §3.2.

中文 —
§1.4 落地两个并存的检索 provider（Candidate + Semantic），会触发 §1.3 Manager 的“单外部 provider”规则。本实现不放宽
该规则，而是把 Composite 注册为**唯一**外部 provider（内置策展存储仍最先），内部容纳子 provider：``prefetch`` 广播并
**归并**（按 ``ENTRY_DELIMITER`` 切分 → 保序 ``dict.fromkeys`` 去重 → 按预算截断）；生命周期钩子扇出；``shutdown``
逆序运行。``sync_turn`` 在给出 ``entity_type`` 时**单播**到归属子 provider，否则扇出。这复用且绝不破坏 §1.3 单 worker /
``flush_pending`` / 有界排空不变量（它在其中运行）。完整 Composite（Employee 子 provider、entity_type + 查询意图路由表、
归并一致性强化、备份聚合）为 Phase 2 §3.2。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..provider import MemoryProvider
from ..store import ENTRY_DELIMITER


class CompositeMemoryProvider(MemoryProvider):
    """A single external provider that routes/merges across sub-providers (name ``"composite"``).

    EN —
    Args (constructor): sub_providers (ordered); char_budget (merge cap). Each sub-provider should
    carry an ``entity_type`` attribute for unicast sync routing.

    中文 —
    参数（构造）：sub_providers（有序）；char_budget（归并上限）。每个子 provider 应带 ``entity_type`` 属性以供单播
    sync 路由。
    """

    def __init__(self, sub_providers: List[MemoryProvider], *, char_budget: int = 4000) -> None:
        """Construct over an ordered list of sub-providers.

        EN: Args: sub_providers; char_budget. 中文：参数：sub_providers；char_budget。
        """
        self._subs = list(sub_providers)
        self._budget = char_budget
        self._route = {getattr(p, "entity_type", p.name): p for p in self._subs}

    @property
    def name(self) -> str:
        """Provider name (the sole external).

        EN: Returns: "composite". 中文：返回："composite"。
        """
        return "composite"

    def is_available(self) -> bool:
        """Available if any sub-provider is.

        EN: Returns: True if any sub is available. 中文：返回：任一子可用则 True。
        """
        return any(p.is_available() for p in self._subs)

    def initialize(self, session_id: str, **kwargs) -> None:
        """Fan out initialize to sub-providers.

        EN: Args: session_id; kwargs. 中文：参数：session_id；kwargs。
        """
        for p in self._subs:
            p.initialize(session_id, **kwargs)

    def get_tool_schemas(self) -> List[dict]:
        """Aggregate sub-providers' tool schemas (none in §1.4).

        EN: Returns: the concatenated schemas. 中文：返回：拼接后的 schema。
        """
        schemas: List[dict] = []
        for p in self._subs:
            schemas.extend(p.get_tool_schemas())
        return schemas

    def system_prompt_block(self) -> str:
        """Concatenate non-empty sub-provider static blocks.

        EN: Returns: blocks joined by blank lines (or ""). 中文：返回：以空行连接的块（或 ""）。
        """
        blocks = [b for p in self._subs if (b := p.system_prompt_block()) and b.strip()]
        return "\n\n".join(blocks)

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        """Broadcast prefetch, then merge + dedup + budget-truncate.

        EN —
        Args: query; session_id. Returns: the merged recall — entries split on ``ENTRY_DELIMITER``,
        order-preserving deduped, kept in order until the char budget, rejoined. Failure-isolated per sub.
        中文 —
        参数：query；session_id。返回：归并后的召回——按 ``ENTRY_DELIMITER`` 切分条目、保序去重、按字符预算依序保留、
        重新连接。每个子 provider 失败隔离。
        """
        parts: List[str] = []
        for p in self._subs:
            try:
                r = p.prefetch(query, session_id=session_id)
            except Exception:
                continue
            if r and r.strip():
                parts.append(r)
        entries = [e.strip() for e in ENTRY_DELIMITER.join(parts).split(ENTRY_DELIMITER) if e.strip()]
        kept: List[str] = []
        total = 0
        for e in dict.fromkeys(entries):  # order-preserving dedup
            add = len(e) + (len(ENTRY_DELIMITER) if kept else 0)
            if total + add > self._budget:
                break
            kept.append(e)
            total += add
        return ENTRY_DELIMITER.join(kept)

    def queue_prefetch(self, query: str, *, session_id: str = "") -> None:
        """Fan out queue_prefetch to sub-providers.

        EN: Args: query; session_id. 中文：参数：query；session_id。
        """
        for p in self._subs:
            p.queue_prefetch(query, session_id=session_id)

    def sync_turn(
        self,
        user_content: str,
        assistant_content: str,
        *,
        session_id: str = "",
        messages: Optional[List[Dict[str, Any]]] = None,
        entity_type: Optional[str] = None,
        agent_context: str = "primary",
        **kwargs,
    ) -> None:
        """Unicast to the owning sub-provider (by entity_type), else fan out; skip non-primary.

        EN —
        Args: user_content; assistant_content; session_id; messages; entity_type (unicast route);
        agent_context (non-primary subagent/cron/flush writes are skipped — Invariant 3). Returns: None.
        中文 —
        参数：user_content；assistant_content；session_id；messages；entity_type（单播路由）；agent_context
        （非 primary 的子代理/cron/flush 写入被跳过——不变量 3）。返回：None。
        """
        if agent_context != "primary":
            return
        targets = [self._route[entity_type]] if entity_type in self._route else self._subs
        for p in targets:
            p.sync_turn(user_content, assistant_content, session_id=session_id, messages=messages)

    def on_pre_compress(self, messages: List[Dict[str, Any]]) -> str:
        """Aggregate sub-providers' pre-compression facts.

        EN: Args: messages. Returns: joined facts (or ""). 中文：参数：messages。返回：连接的事实（或 ""）。
        """
        parts = [r for p in self._subs if (r := p.on_pre_compress(messages)) and r.strip()]
        return "\n\n".join(parts)

    def on_session_switch(self, new_session_id: str, *, parent_session_id: str = "", reset: bool = False, **kwargs) -> None:
        """Fan out a session switch to sub-providers.

        EN: Args: new_session_id; parent_session_id; reset; kwargs. 中文：参数：见英文。
        """
        for p in self._subs:
            p.on_session_switch(new_session_id, parent_session_id=parent_session_id, reset=reset, **kwargs)

    def on_delegation(self, task: str, result: str, *, child_session_id: str = "", **kwargs) -> None:
        """Fan out a delegation observation to sub-providers.

        EN: Args: task; result; child_session_id; kwargs. 中文：参数：见英文。
        """
        for p in self._subs:
            p.on_delegation(task, result, child_session_id=child_session_id, **kwargs)

    def on_memory_write(self, action: str, target: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Fan out a memory-write mirror to sub-providers.

        EN: Args: action; target; content; metadata. 中文：参数：见英文。
        """
        for p in self._subs:
            p.on_memory_write(action, target, content, metadata=metadata)

    def clear_recall_cache(self) -> None:
        """Fan out a recall-cache clear to sub-providers that maintain one (the §1.5 erasure pipeline).

        EN: Returns: None. Sub-providers without a cache (e.g. the builtin) are skipped.
        中文：返回：None。无缓存的子 provider（如内置）跳过。
        """
        for p in self._subs:
            clear = getattr(p, "clear_recall_cache", None)
            if callable(clear):
                clear()

    def backup_paths(self) -> List[str]:
        """Merge the external storage paths declared by sub-providers.

        EN: Returns: the union of sub-provider backup paths. 中文：返回：子 provider 备份路径的并集。
        """
        paths: List[str] = []
        for p in self._subs:
            paths.extend(p.backup_paths())
        return paths

    def shutdown(self) -> None:
        """Shut down sub-providers in reverse order (consistent with the Manager).

        EN: Returns: None. 中文：返回：None。
        """
        for p in reversed(self._subs):
            p.shutdown()
