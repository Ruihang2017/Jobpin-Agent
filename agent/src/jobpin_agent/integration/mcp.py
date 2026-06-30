"""MCP tool-exposure skeleton (§1.10) — connector operations as ToolSpecs in the ToolRegistry.

EN —
Integrations are exposed to the agent as tools rather than per-integration glue (PRD §2.5). This skeleton
renders each connector operation as a §1.1 ``ToolSpec`` (the MCP tool shape: name / description / JSON-schema
parameters / handler) and registers it in the existing ``ToolRegistry`` — so the agent can call
``fake-ats_pull_candidate`` like any other tool. The handler runs ``IntegrationService.ingest`` and returns
a short summary string; if the fully-local switch blocks the egress it returns a "blocked" message rather
than raising into the loop. A live MCP **server/transport** (JSON-RPC over stdio/SSE) is deliberately NOT
built here — that feasibility/cost is the §1.12 spike 5; this skeleton is transport-agnostic.

中文 —
集成以工具而非逐集成胶水暴露给 agent（PRD §2.5）。本骨架把每个连接器操作渲染为 §1.1 ``ToolSpec``（MCP 工具形态：名称 /
描述 / JSON-schema 参数 / 处理函数）并注册进既有 ``ToolRegistry``——使 agent 可像调用任何工具一样调用
``fake-ats_pull_candidate``。处理函数运行 ``IntegrationService.ingest`` 并返回简短摘要字符串；若完全本地开关阻断出站，
则返回“已阻断”消息而非向循环抛错。这里刻意**不**建真实 MCP **服务端/传输**（JSON-RPC over stdio/SSE）——其可行性/成本是
§1.12 spike 5；本骨架与传输无关。
"""
from __future__ import annotations

from typing import List

from ..core.tools import ToolRegistry, ToolSpec
from .outbound import OutboundBlocked
from .sdk import AntiCorruptionLayer, Connector
from .service import IntegrationService


def connector_toolspecs(service: IntegrationService, connector: Connector,
                        acl: AntiCorruptionLayer, kinds: List[str]) -> List[ToolSpec]:
    """Build one ``ToolSpec`` per (connector, kind) wrapping ``IntegrationService.ingest``.

    EN —
    Args: service; connector; acl; kinds (the entity kinds to expose, e.g. ``["candidate", "job"]``).
    Returns: a list of ``ToolSpec`` named ``{connector.name}_pull_{kind}``. Each handler ingests and
    returns a summary string; a fully-local block returns a "blocked" message (never raises into the loop).

    中文 —
    参数：service；connector；acl；kinds（要暴露的实体类型，如 ``["candidate", "job"]``）。返回：名为
    ``{connector.name}_pull_{kind}`` 的 ``ToolSpec`` 列表。每个处理函数执行 ingest 并返回摘要字符串；完全本地阻断时
    返回“已阻断”消息（绝不向循环抛错）。
    """
    specs: List[ToolSpec] = []
    for kind in kinds:
        def make_handler(bound_kind: str):
            def handler(_args: dict) -> str:
                try:
                    res = service.ingest(connector, acl, bound_kind)
                    return f"Ingested {res.count} {bound_kind}(s) from {connector.name} into the local store."
                except OutboundBlocked:
                    return (f"blocked: fully-local mode is on; {connector.name} egress is disabled. "
                            f"Turn off the fully-local switch to allow this outbound pull.")
            return handler

        specs.append(ToolSpec(
            name=f"{connector.name}_pull_{kind}",
            description=(f"Pull {kind} records from the {connector.name} connector into the local store "
                        f"(outbound; governed by the fully-local switch)."),
            parameters={"type": "object", "properties": {}},
            handler=make_handler(kind),
        ))
    return specs


def register_connector(registry: ToolRegistry, *toolspecs: ToolSpec) -> None:
    """Register connector ``ToolSpec``s into a ``ToolRegistry``.

    EN — Args: registry; *toolspecs. Returns: None. 中文 — 参数：registry；*toolspecs。返回：None。
    """
    for spec in toolspecs:
        registry.register(spec)
