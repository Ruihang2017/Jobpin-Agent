# `integration/` — Integration framework (§1.10)

## English
Translates external systems (ATS/HRIS/calendar/email) into §1.8 canonical entities, exposes connector
operations as MCP-shaped tools, and routes every outbound call through a default-on "fully local" switch
with a per-egress audit. Phase 0 ships the framework + a **fake** read-only ATS; the **live** real-ATS
connection is deferred until real credentials + the §1.11 de-id pipeline exist (Plan §1.10 scope decision).
See the devlog `../../../../site/devlog/p0-1.10-integration-EN.md`.

- `sdk.py` — `ExternalRecord` (opaque external row); `Connector` (ABC, read-only `fetch(kind)`);
  `AntiCorruptionLayer` (ABC — the ONLY place external field names are read; `translate` dispatches by kind,
  unknown kind → `ValueError`).
- `outbound.py` — `OutboundGuard` (the single outbound chokepoint; `fully_local` defaults **True** ⇒ 0
  outbound; egress audit via the §1.8 `AuditStore` with the true outcome) + `OutboundBlocked`.
- `service.py` — `IntegrationService.ingest` (validate kind → guard-gated fetch → anti-corruption translate
  → §1.8 `CanonicalStore.upsert_*`) + `IngestResult`.
- `mcp.py` — `connector_toolspecs` (connector ops → §1.1 `ToolSpec`s) + `register_connector`. A live MCP
  server/transport is the §1.12 spike; this is the transport-agnostic skeleton.
- `connectors/` — concrete connectors (Phase 0: `fake_ats` only).

## 中文
把外部系统（ATS/HRIS/日历/邮件）翻译为 §1.8 规范实体，将连接器操作以 MCP 形态的工具暴露，并使每次出站经过默认开启的
“完全本地”开关与逐次出站审计。Phase 0 交付框架 + **伪**只读 ATS；**真实** ATS 实时连接推迟到具备真实凭据 + §1.11 脱敏
管线时（计划 §1.10 范围决策）。见开发日志 `../../../../site/devlog/p0-1.10-integration.md`。

- `sdk.py` — `ExternalRecord`（不透明外部行）；`Connector`（ABC，只读 `fetch(kind)`）；`AntiCorruptionLayer`
  （ABC——读取外部字段名的唯一之处；`translate` 按 kind 分派，未知 kind → `ValueError`）。
- `outbound.py` — `OutboundGuard`（唯一出站口；`fully_local` 默认 **True** ⇒ 0 出站；经 §1.8 `AuditStore` 按真实结果
  做出站审计）+ `OutboundBlocked`。
- `service.py` — `IntegrationService.ingest`（先校验 kind → 经守卫的 fetch → 反腐层翻译 → §1.8
  `CanonicalStore.upsert_*`）+ `IngestResult`。
- `mcp.py` — `connector_toolspecs`（连接器操作 → §1.1 `ToolSpec`）+ `register_connector`。真实 MCP 服务端/传输是
  §1.12 spike；本节为与传输无关的骨架。
- `connectors/` — 具体连接器（Phase 0：仅 `fake_ats`）。
