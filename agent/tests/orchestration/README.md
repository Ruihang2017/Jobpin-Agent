# `agent/tests/orchestration/` — §1.7 Layer B tests

## English
Deterministic, offline tests for the orchestration skeleton. Run with
`cd agent && python -m pytest tests/orchestration`.

- `test_store.py` — instance round-trip; append-only ordered transitions; non-terminal filter; idempotency get/put.
- `test_state_machine.py` — start + initial state; legal/illegal transitions; await/resume HITL; history append; fail.
- `test_idempotency.py` — run-once dedup; replay after a (file-DB) restart does not re-send.
- `test_recovery.py` — recover returns only the non-terminal instances.
- `test_persistence_contracts.py` — the three exit-criteria contracts (crash recovery / cross-day pause-resume /
  side-effect idempotency) end-to-end with a toy process over a file DB.

## 中文
编排骨架的确定性离线测试。运行：`cd agent && python -m pytest tests/orchestration`。

- `test_store.py` — 实例往返；仅追加且有序的转移；非终止过滤；幂等 get/put。
- `test_state_machine.py` — start + 初始状态；合法/非法转移；await/resume HITL；历史追加；fail。
- `test_idempotency.py` — run-once 去重；（文件 DB）重启后重放不重发。
- `test_recovery.py` — recover 仅返回非终止实例。
- `test_persistence_contracts.py` — 三条退出标准契约（崩溃恢复 / 跨天暂停-恢复 / 副作用幂等）以玩具流程在文件 DB 上端到端。
