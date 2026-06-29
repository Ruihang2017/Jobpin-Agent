# `core/` — Agent Core (Layer A)

## English
The local, provider-agnostic agent runtime (Production Plan §1.1). It completes one
turn — system-prompt assembly → tool-call loop → sub-agent delegation — and exposes
the seam that the Memory Subsystem (§1.2–1.6) plugs into.

- `messages.py` — provider-agnostic conversation types (`Role`, `Message`, `ToolCall`, `ToolResult`, `ModelResponse`).
- `tools.py` — `ToolSpec`, `ToolRegistry`, the `echo` demo tool.
- `system_prompt.py` — deterministic system-prompt assembler (golden-snapshot tested).
- `tracing.py` — step-level tracer (`Tracer`, `TraceEvent`).
- `hooks.py` — `MemoryHooks` protocol + `NoOpHooks` (the memory seam).
- `session_store.py` — SQLite session store with branch/reset + `compact` (§1.6 compression).
- `config.py` — env-based `CoreConfig`.
- `agent_loop.py` — the synchronous turn loop (`Agent`, `TurnResult`); §1.6 adds the opt-in `compressor`.
- `compression.py` — §1.6 `ContextCompressor` + `default_summarize` (pre-compression fact-injection wiring).
- `delegation.py` — sub-agent delegation (`delegate`, `DelegationResult`).
- `model/` — the provider-agnostic model layer (ABC + adapters).

## 中文
本地、provider 无关的 agent 运行时（生产计划 §1.1）。它完成一个回合——系统提示装配 → 工具调用循环 → 子代理委派
——并暴露记忆子系统（§1.2–1.6）接入的接缝。

- `messages.py` — provider 无关的会话类型（`Role`、`Message`、`ToolCall`、`ToolResult`、`ModelResponse`）。
- `tools.py` — `ToolSpec`、`ToolRegistry`、`echo` 演示工具。
- `system_prompt.py` — 确定性系统提示装配器（黄金快照测试）。
- `tracing.py` — 步骤级追踪器（`Tracer`、`TraceEvent`）。
- `hooks.py` — `MemoryHooks` 协议 + `NoOpHooks`（记忆接缝）。
- `session_store.py` — 带 branch/reset 的 SQLite 会话存储 + `compact`（§1.6 压缩）。
- `config.py` — 基于环境变量的 `CoreConfig`。
- `agent_loop.py` — 同步回合循环（`Agent`、`TurnResult`）；§1.6 加入可选 `compressor`。
- `compression.py` — §1.6 `ContextCompressor` + `default_summarize`（压缩前事实注入接线）。
- `delegation.py` — 子代理委派（`delegate`、`DelegationResult`）。
- `model/` — provider 无关的模型层（抽象基类 + 适配器）。
