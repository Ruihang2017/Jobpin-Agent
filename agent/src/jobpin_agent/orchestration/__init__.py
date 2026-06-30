"""Layer B — long-running business-process orchestration (§1.7).

EN —
The state-machine layer Hermes lacks. Layer A (§1.1–§1.6: agent loop + memory) is single-shot inference;
Layer B is the **cross-day, multi-party, resumable** business process — the hiring loop (PRD §2.6/§13.1).
This package is a lightweight, in-house state machine that satisfies three hard persistence contracts:
crash recovery, cross-day pause/resume, and external side-effect idempotency. It builds only the
**skeleton + primitives** (state definition / transition / persistence / idempotency / HITL break point);
the real recruitment-process states are filled at Phase 1 M3, and the upgrade to Temporal/LangGraph is
reserved for if/when the skeleton fails the contract (§1.12 spike). Net-new code (no Hermes port).

中文 —
Hermes 缺失的状态机层。Layer A（§1.1–§1.6：agent 循环 + 记忆）是单次推理；Layer B 是**跨天、多方、可恢复**的业务流程
——招聘 loop（PRD §2.6/§13.1）。本包是一个轻量、自建的状态机，满足三条硬持久化契约：崩溃恢复、跨天暂停/恢复、外部
副作用幂等。它仅构建**骨架 + 原语**（状态定义 / 转移 / 持久化 / 幂等 / HITL 断点）；真实招聘流程状态在第一阶段 M3 填充，
升级到 Temporal/LangGraph 保留至骨架未达契约时（§1.12 spike）。新增代码（非 Hermes 移植）。
"""
