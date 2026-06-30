"""Integration framework (§1.10) — external systems → §1.8 canonical entities, via MCP tools, local-first.

EN — The uniform skeleton that translates external systems (ATS/HRIS/calendar/email) into canonical
entities through an anti-corruption layer, exposes connector operations as MCP-shaped tools, and routes
every outbound call through a default-on "fully local" switch with a per-egress audit. Phase 0 ships the
framework + a fake read-only ATS; the live real-ATS connection is deferred (Plan §1.10 scope decision).

中文 — 统一骨架：经反腐层把外部系统（ATS/HRIS/日历/邮件）翻译为规范实体，将连接器操作以 MCP 形态的工具暴露，并使每次
出站都经过默认开启的“完全本地”开关与逐次出站审计。Phase 0 交付框架 + 伪只读 ATS；真实 ATS 实时连接推迟（计划 §1.10
范围决策）。
"""
