# `agent/tests/governance/` — §1.5 governance tests

## English
Deterministic unit + integration tests for the §1.5 HR memory governance package. All run offline with
`:memory:` SQLite. Run with `cd agent && python -m pytest tests/governance`.

- `test_namespace.py` — key parse/format/validate + prefix levels.
- `test_labels.py` — governance-header render/parse round-trip + the consent-required set.
- `test_audit.py` — append-only log, dual timestamp, filtered query.
- `test_bias_hygiene.py` — reject protected attributes, flag proxies, pass clean text.
- `test_rbac.py` — Principal scope predicate (prefix match) + full access.
- `test_retention.py` — policy registry, TTL sweep, backup-ageing register.
- `test_write_gate.py` — reject missing provenance/consent/bias; accept labelled writes.
- `test_governed_tool.py` — the governed `memory` tool on `BuiltinMemoryProvider` (reject/commit/no-gate).
- `test_erasure.py` — the data-subject erasure drill (exit criterion 2).
- `test_governance_end_to_end.py` — governed write through `Agent.run_turn` + RBAC recall isolation
  (no loop change).

## 中文
§1.5 HR 记忆治理包的确定性单元 + 集成测试。全部离线运行，用 `:memory:` SQLite。运行：
`cd agent && python -m pytest tests/governance`。

- `test_namespace.py` — 键 parse/format/validate + 前缀级别。
- `test_labels.py` — 治理头 render/parse 往返 + 需要同意的集合。
- `test_audit.py` — 仅追加日志、双时间戳、过滤查询。
- `test_bias_hygiene.py` — 拒绝受保护属性、标记代理变量、放行干净文本。
- `test_rbac.py` — Principal 范围谓词（前缀匹配）+ 全访问。
- `test_retention.py` — 策略注册表、TTL 扫描、备份老化注册表。
- `test_write_gate.py` — 拒绝缺失来源/同意/偏见；接受标注写入。
- `test_governed_tool.py` — `BuiltinMemoryProvider` 上的受治理 `memory` 工具（拒绝/提交/无门控）。
- `test_erasure.py` — 数据主体擦除演练（退出标准 2）。
- `test_governance_end_to_end.py` — 经 `Agent.run_turn` 的受治理写入 + RBAC 召回隔离（不改循环）。
