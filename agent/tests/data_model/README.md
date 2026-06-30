# `agent/tests/data_model/` — §1.8 canonical data + audit tests

(Named `data_model/` to avoid colliding with `tests/data/`, which holds the system-prompt golden fixture.)

## English
Deterministic, offline tests for the §1.8 canonical data model + local audit log. Run with
`cd agent && python -m pytest tests/data_model`.

- `test_schema.py` — entity dataclasses + DDL presence for the M1–M3 subset + seam tables.
- `test_migrations.py` — migrations roll forward to LATEST, back to 0, and re-forward (the exit criterion).
- `test_audit.py` — canonical audit: write/erase/recall + a rejected op recorded & queryable; append-only;
  reconciliation import of the §1.5 governance audit + §1.7 transitions.
- `test_store.py` — `CanonicalStore` CRUD round-trips (candidate / memory-record / the rest) + shared audit.

## 中文
§1.8 规范数据模型 + 本地审计日志的确定性离线测试。运行：`cd agent && python -m pytest tests/data_model`。
（命名为 `data_model/` 以避免与持有系统提示黄金固定装置的 `tests/data/` 冲突。）

- `test_schema.py` — M1–M3 子集 + 接缝表的实体数据类与 DDL 存在性。
- `test_migrations.py` — 迁移前滚到 LATEST、后滚到 0、再前滚（退出标准）。
- `test_audit.py` — 规范审计：写/擦除/召回 + 被拒操作记录且可查询；仅追加；§1.5 治理审计 + §1.7 转移的对账导入。
- `test_store.py` — `CanonicalStore` CRUD 往返（候选人/记忆记录/其余）+ 共享审计。
