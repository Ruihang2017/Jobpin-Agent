# `agent/tests/security/` — §1.6 injection-defence tests

## English
Deterministic, offline tests for the §1.6 context-window security package. Run with
`cd agent && python -m pytest tests/security`.

- `test_threat_patterns.py` — injection/exfil/C2 variants flagged at the right scope; multi-word bypass;
  invisible unicode; benign HR text passes at `context`; scope widening.
- `test_scrubber.py` — cross-chunk fence split (no leak); unclosed span discarded on flush; passthrough.
- `test_external_ingest.py` — clean text fenced; adversarial text blocked, never returned raw.
- `test_scan_wiring.py` — `build_memory_backend` defaults to the strict scan ([BLOCKED] in the snapshot);
  explicit pass-through override; context-scope role-hijack catch.

(The compression wiring is tested in `../test_compression.py` + `../test_compression_loop.py`.)

## 中文
§1.6 上下文窗口安全包的确定性离线测试。运行：`cd agent && python -m pytest tests/security`。

- `test_threat_patterns.py` — 注入/外泄/C2 变体在正确范围被标记；多词绕过；不可见 unicode；良性 HR 文本在 `context`
  通过；范围放大。
- `test_scrubber.py` — 跨块围栏切分（不泄漏）；未关闭 span 在 flush 时丢弃；透传。
- `test_external_ingest.py` — 干净文本被围栏；对抗文本被阻断且绝不原样返回。
- `test_scan_wiring.py` — `build_memory_backend` 默认 strict 扫描（快照中 [BLOCKED]）；显式 pass-through 覆盖；
  context 范围角色劫持命中。

（压缩接线在 `../test_compression.py` + `../test_compression_loop.py` 测试。）
