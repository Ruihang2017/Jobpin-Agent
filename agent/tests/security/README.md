# `agent/tests/security/` — §1.6 injection-defence + §1.9 security-baseline tests

## English
Deterministic, offline tests for the `security/` package (§1.6 injection defence + §1.9 security baseline).
Run with `cd agent && python -m pytest tests/security`.

**§1.9 — security baseline:**
- `test_sqlcipher_smoke.py` — dependency de-risk: a keyed SQLCipher DB is ciphertext on disk, wrong key fails, right key reads back.
- `test_cipher.py` — AES-256-GCM round-trip, random nonce, tamper raises, bad key length, HKDF subkey separation.
- `test_keystore.py` — DevKeyStore stable; master key never equals the on-disk wrapped bytes; DPAPI round-trip (Windows-only).
- `test_db_encryption.py` — `open_encrypted_db`: ciphertext when keyed (key-gated read), plain sqlite passthrough when not.
- `test_rbac_engine.py` — the unauthorised-access matrix: cross-org / missing-permission / sensitivity-ceiling / org↔key-mismatch / unknown-role denials (`rejected:rbac`) + in-scope/admin allows.
- `test_encryption_wiring.py` — the §1.8 `CanonicalStore` is ciphertext at rest when keyed (plain by default); keystore→cipher→store end-to-end.
- `test_file_store_encryption.py` — the §1.2 `MemoryStore` ORG.md is ciphertext at rest + round-trips; plaintext by default; drift `.bak` leaks no plaintext under encryption.

(The config fail-loud guard for `encryption_enabled` is tested in `../test_config.py`.)

**§1.6 — injection defence:**
- `test_threat_patterns.py` — injection/exfil/C2 variants flagged at the right scope; multi-word bypass;
  invisible unicode; benign HR text passes at `context`; scope widening.
- `test_scrubber.py` — cross-chunk fence split (no leak); unclosed span discarded on flush; passthrough.
- `test_external_ingest.py` — clean text fenced; adversarial text blocked, never returned raw.
- `test_scan_wiring.py` — `build_memory_backend` defaults to the strict scan ([BLOCKED] in the snapshot);
  explicit pass-through override; context-scope role-hijack catch.

(The compression wiring is tested in `../test_compression.py` + `../test_compression_loop.py`.)

## 中文
`security/` 包的确定性离线测试（§1.6 注入防御 + §1.9 安全基线）。运行：`cd agent && python -m pytest tests/security`。

**§1.9 — 安全基线：**
- `test_sqlcipher_smoke.py` — 依赖去风险：带密钥的 SQLCipher 库落盘为密文，错误密钥失败，正确密钥读回。
- `test_cipher.py` — AES-256-GCM 往返、随机 nonce、篡改抛错、错误密钥长度、HKDF 子密钥分离。
- `test_keystore.py` — DevKeyStore 稳定；主密钥绝不等于落盘封装字节；DPAPI 往返（仅 Windows）。
- `test_db_encryption.py` — `open_encrypted_db`：带密钥时密文（按密钥门控读取），否则普通 sqlite 透传。
- `test_rbac_engine.py` — 越权访问矩阵：跨 org / 缺权限 / 敏感度上限 / org 与键不一致 / 未知角色 拒绝（`rejected:rbac`）+ 范围内/admin 放行。
- `test_encryption_wiring.py` — §1.8 `CanonicalStore` 带密钥时静态为密文（默认明文）；keystore→cipher→store 全链路。
- `test_file_store_encryption.py` — §1.2 `MemoryStore` ORG.md 静态为密文且往返；默认明文；加密下漂移 `.bak` 不泄漏明文。

（`encryption_enabled` 的失败即响守卫在 `../test_config.py` 测试。）

**§1.6 — 注入防御：**
- `test_threat_patterns.py` — 注入/外泄/C2 变体在正确范围被标记；多词绕过；不可见 unicode；良性 HR 文本在 `context`
  通过；范围放大。
- `test_scrubber.py` — 跨块围栏切分（不泄漏）；未关闭 span 在 flush 时丢弃；透传。
- `test_external_ingest.py` — 干净文本被围栏；对抗文本被阻断且绝不原样返回。
- `test_scan_wiring.py` — `build_memory_backend` 默认 strict 扫描（快照中 [BLOCKED]）；显式 pass-through 覆盖；
  context 范围角色劫持命中。

（压缩接线在 `../test_compression.py` + `../test_compression_loop.py` 测试。）
