# `agent/tests/integration/` — §1.10 integration-framework tests

## English
Deterministic, offline tests for the `integration/` package. Run: `cd agent && python -m pytest tests/integration`.

- `test_anti_corruption.py` — the fake ATS's external field names translate to §1.8 candidate/job/application fields; unknown kind raises.
- `test_outbound_guard.py` — fully-local ⇒ block + call spy 0 + `rejected:fully_local` row; switch-off ⇒ run + `ok` row; a failed call ⇒ `error` row + re-raise.
- `test_ingest_pipeline.py` — exit 1: switch-off pull→translate→CanonicalStore; exit 2 (dedicated): fully-local ⇒ 0 outbound, nothing ingested; unknown kind raises before any egress.
- `test_mcp_exposure.py` — connector ops register as ToolSpecs + run the ingest handler; two-kind binding; fully-local handler returns the blocked string.

## 中文
`integration/` 包的确定性离线测试。运行：`cd agent && python -m pytest tests/integration`。

- `test_anti_corruption.py` — 伪 ATS 外部字段名翻译为 §1.8 候选人/职位/申请字段；未知 kind 抛错。
- `test_outbound_guard.py` — 完全本地 ⇒ 阻断 + call spy 0 + `rejected:fully_local` 行；关闭 ⇒ 运行 + `ok` 行；失败调用 ⇒ `error` 行 + 重抛。
- `test_ingest_pipeline.py` — 退出 1：关闭时拉取→翻译→CanonicalStore；退出 2（专项）：完全本地 ⇒ 0 出站、无入库；未知 kind 在任何出站前抛错。
- `test_mcp_exposure.py` — 连接器操作注册为 ToolSpec + 运行 ingest 处理函数；两类绑定；完全本地处理函数返回阻断字符串。
