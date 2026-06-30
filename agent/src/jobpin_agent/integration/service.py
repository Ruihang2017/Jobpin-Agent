"""IntegrationService (§1.10) — the ingest orchestrator: guard-gated pull → anti-corruption → §1.8 store.

EN —
Ties the pieces together. ``ingest`` routes the connector's (conceptually outbound) ``fetch`` through the
``OutboundGuard`` — so a fully-local run raises ``OutboundBlocked`` before any fetch (0 outbound, 0
ingested) — then translates each external record through the anti-corruption layer into a §1.8 canonical
entity and upserts it into the local ``CanonicalStore`` (encrypted at rest when the store is §1.9-keyed).
This is the single place the read-only-pull pipeline lives; the MCP tools (``mcp.py``) just wrap it.

中文 —
把各部分串起来。``ingest`` 把连接器（概念上出站的）``fetch`` 经 ``OutboundGuard`` 路由——故完全本地运行会在任何 fetch
之前抛 ``OutboundBlocked``（0 出站、0 入库）——随后把每条外部记录经反腐层翻译为 §1.8 规范实体并 upsert 进本地
``CanonicalStore``（当存储以 §1.9 加密时静态加密）。这是只读拉取管线唯一所在；MCP 工具（``mcp.py``）只是包裹它。
"""
from __future__ import annotations

from dataclasses import dataclass

from ..data.store import CanonicalStore
from .outbound import OutboundGuard
from .sdk import AntiCorruptionLayer, Connector


@dataclass(frozen=True)
class IngestResult:
    """The outcome of an ingest run.

    EN — Attributes: kind (the entity kind ingested); count (how many records were upserted).
    中文 — 属性：kind（入库的实体类型）；count（upsert 的记录数）。
    """

    kind: str
    count: int


class IntegrationService:
    """Pull → translate → store, gated by the fully-local switch.

    EN — Args (constructor): store (§1.8 ``CanonicalStore``); guard (§1.10 ``OutboundGuard``).
    中文 — 参数（构造器）：store（§1.8 ``CanonicalStore``）；guard（§1.10 ``OutboundGuard``）。
    """

    def __init__(self, store: CanonicalStore, guard: OutboundGuard) -> None:
        """Args: store; guard. 中文 — 参数：store；guard。"""
        self._store = store
        self._guard = guard

    def ingest(self, connector: Connector, acl: AntiCorruptionLayer, kind: str) -> IngestResult:
        """Pull ``kind`` from ``connector`` (gated), translate via ``acl``, upsert into the local store.

        EN —
        Args: connector; acl; kind (``candidate``/``job``/``application``). Returns: ``IngestResult``.
        Raises: ``OutboundBlocked`` if the fully-local switch is on (the fetch never runs); ``ValueError``
            on an unknown kind (from the ACL).

        中文 —
        参数：connector；acl；kind（``candidate``/``job``/``application``）。返回：``IngestResult``。
        抛出：完全本地开关打开时抛 ``OutboundBlocked``（fetch 绝不运行）；未知 kind 时抛 ``ValueError``（来自 ACL）。
        """
        records = self._guard.send(
            target=connector.name, fields=[kind], reason=f"pull:{kind}",
            call=lambda: connector.fetch(kind),
        )
        upsert = {
            "candidate": self._store.upsert_candidate,
            "job": self._store.upsert_job,
            "application": self._store.upsert_application,
        }[kind]
        count = 0
        for rec in records:
            upsert(acl.translate(rec))
            count += 1
        return IngestResult(kind=kind, count=count)
