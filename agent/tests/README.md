# `agent/tests/` — the test suite

## English
Pytest tests for the agent core. One test module per source module; all run
offline and deterministically (the OpenAI integration test skips unless
`OPENAI_API_KEY` is set). Run with `cd agent && python -m pytest`.

- `test_smoke.py` — package imports + `__version__`.
- `test_fake_provider.py` — the scripted test double.
- `test_tools.py` — tool registry register/execute/unknown.
- `test_system_prompt.py` — golden snapshot + 100x determinism.
- `test_tracing.py` — ordered events + JSONL.
- `test_hooks.py` — `NoOpHooks` defaults + protocol.
- `test_session_store.py` — round-trip, branch, reset, session-switch.
- `test_agent_loop.py` — the four loop paths + recall/snapshot separation.
- `test_delegation.py` — skip_memory child + parent observation.
- `test_openai_provider.py` — wire mapping, kwargs, opt-in integration.
- `test_demo.py` — the runnable demo, offline.
- `test_compression.py` — §1.6 `ContextCompressor` + `SessionStore.compact` (capture/merge `on_pre_compress`).
- `test_compression_loop.py` — §1.6 opt-in compression through `Agent.run_turn` (fact survives; off = unchanged).
- `governance/` — §1.5 HR memory governance tests (see its own README).
- `security/` — §1.6 injection-defence tests (threat patterns, scrubber, ingest, scan wiring; see its own README).
- `data/` — fixtures (the system-prompt golden file).

## 中文
Agent 内核的 pytest 测试。每个源模块对应一个测试模块；全部离线且确定性运行（OpenAI 集成测试在未设置
`OPENAI_API_KEY` 时跳过）。运行：`cd agent && python -m pytest`。

- `test_smoke.py` — 包导入 + `__version__`。
- `test_fake_provider.py` — 脚本化测试替身。
- `test_tools.py` — 工具注册表 注册/执行/未知。
- `test_system_prompt.py` — 黄金快照 + 100 次确定性。
- `test_tracing.py` — 有序事件 + JSONL。
- `test_hooks.py` — `NoOpHooks` 默认值 + 协议。
- `test_session_store.py` — 往返、branch、reset、会话切换。
- `test_agent_loop.py` — 四条循环路径 + 召回/快照分离。
- `test_delegation.py` — skip_memory 子代理 + 父代理观察。
- `test_openai_provider.py` — 线映射、kwargs、可选集成。
- `test_demo.py` — 可运行演示，离线。
- `test_compression.py` — §1.6 `ContextCompressor` + `SessionStore.compact`（捕获/并入 `on_pre_compress`）。
- `test_compression_loop.py` — §1.6 经 `Agent.run_turn` 的可选压缩（事实存活；关闭则不变）。
- `governance/` — §1.5 HR 记忆治理测试（见其自身 README）。
- `security/` — §1.6 注入防御测试（威胁模式、清洗器、ingest、扫描接线；见其自身 README）。
- `data/` — 固定装置（系统提示黄金文件）。
