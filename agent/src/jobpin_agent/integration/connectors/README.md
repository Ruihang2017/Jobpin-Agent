# `integration/connectors/` — concrete connectors (§1.10)

## English
One module per external system. Phase 0 ships only the fake; live connectors (with OAuth) are deferred until
real credentials + the §1.11 de-id pipeline exist.

- `fake_ats.py` — `FakeATSConnector` (a read-only, synthetic, network-free sample over in-memory fixtures
  whose external field names deliberately DIFFER from the canonical schema) + `FakeATSAntiCorruption` (maps
  those fields to §1.8 `Candidate`/`Job`/`Application`). Used by the §1.10 contract tests.

## 中文
每个外部系统一个模块。Phase 0 仅交付伪连接器；真实连接器（含 OAuth）推迟到具备真实凭据 + §1.11 脱敏管线时。

- `fake_ats.py` — `FakeATSConnector`（基于内存固定数据、只读、合成、无网络的样例，其外部字段名刻意与规范 schema **不同**）
  + `FakeATSAntiCorruption`（把这些字段映射到 §1.8 `Candidate`/`Job`/`Application`）。供 §1.10 契约测试使用。
