# `security/` — Context-window security (§1.6) + security baseline (§1.9)

## English
The product's security layer. §1.6 is injection defence (ported from Hermes, MIT); §1.9 is the security
baseline — at-rest encryption + the RBAC/ABAC engine (net-new). Résumés, emails, and JDs are untrusted
input and a real prompt-injection surface, so external text is scanned and fenced before it reaches the
model's context or memory; local data + memory are encrypted at rest; access is least-privilege. The
threat library and the streaming scrubber are **ported from Hermes (MIT)** — see
`../../../THIRD_PARTY_NOTICES.md`.

**§1.9 — security baseline (net-new):**
- `cipher.py` — `Cipher` (AES-256-GCM, random-nonce AEAD) + `derive_subkey(master, label)` (HKDF-SHA256,
  one master key → independent `db`/`file` subkeys). The one place the `cryptography` dep is used.
- `keystore.py` — `KeyStore` ABC + `WindowsDpapiKeyStore` (ctypes `CryptProtectData`), `MacKeychainKeyStore`
  (the `security` CLI), `DevKeyStore` (INSECURE, CI/Linux only) + `default_keystore(path)`. Holds the master
  key; never at-rest plaintext.
- `db_encryption.py` — `open_encrypted_db(path, key, **kw)` → a keyed SQLCipher connection when `key` is
  given, else a plain `sqlite3` passthrough (the default). The single seam every SQLite store opens through.
- `rbac.py` — the RBAC/ABAC engine: `Role`/`ROLE_POLICIES`, `principal_for(User, Org)->Principal`,
  `authorize(Principal, action, ResourceRef)->Decision` (`rejected:rbac`). The **same source** as the §1.5
  recall filter — it reuses `governance/rbac.py`'s `Principal`/`scope_predicate`.

At-rest encryption is opt-in (a store `cipher_key`/`cipher`; `CoreConfig.encryption_enabled` is a seam that
fails loud until a composition root wires it). See `../../../../docs/security/p0-1.9-threat-model-v1.md`.

**§1.6 — injection defence (ported):**

- `threat_patterns.py` — **ported** from Hermes `tools/threat_patterns.py` (MIT). The 3-scope pattern
  library (`all` ⊂ `context` ⊂ `strict`) + `scan_for_threats(content, scope)` + `first_threat_message(content,
  scope)` (= the §1.2 `scan_entry` seam shape) + `INVISIBLE_CHARS`. Keeps the `(?:\w+\s+)*` multi-word-bypass
  guard and C2-vocabulary anchoring (not bossy English). Memory writes use `strict`.
- `scrubber.py` — **ported** from Hermes `StreamingContextScrubber`. A cross-chunk `feed`/`flush`/`reset`
  state machine that scrubs `<memory-context>` spans split across streamed deltas; an unclosed span is
  discarded on `flush`. The streaming counterpart of the §1.3 fence; the real streaming model path is §1.11.
- `external_ingest.py` — **new**. `ingest_external_text(text, *, source, scope)` — the single door for
  external text: scan → block on a threat hit, else wrap in the §1.3 `<memory-context>` fence.

The pre-compression fact-injection wiring (the other §1.6 deliverable) lives in `core/compression.py`; the
real strict scan is wired into the curated store via `memory/composition.build_memory_backend`.

## 中文
产品的安全层。§1.6 为注入防御（移植自 Hermes，MIT）；§1.9 为安全基线——静态加密 + RBAC/ABAC 引擎（新增）。
简历、邮件与 JD 是不可信输入且为真实提示注入面，故外部文本在进入模型上下文或记忆前被扫描与围栏；本地数据与记忆
静态加密；访问遵循最小权限。威胁库与流式清洗器**移植自 Hermes（MIT）**——见 `../../../THIRD_PARTY_NOTICES.md`。

**§1.9 — 安全基线（新增）：**
- `cipher.py` — `Cipher`（AES-256-GCM，随机 nonce 的 AEAD）+ `derive_subkey(master, label)`（HKDF-SHA256，
  一把主密钥 → 相互独立的 `db`/`file` 子密钥）。`cryptography` 依赖唯一使用处。
- `keystore.py` — `KeyStore` 抽象基类 + `WindowsDpapiKeyStore`（ctypes `CryptProtectData`）、
  `MacKeychainKeyStore`（`security` 命令行）、`DevKeyStore`（**不安全**，仅 CI/Linux）+ `default_keystore(path)`。
  持有主密钥；绝不静态明文。
- `db_encryption.py` — `open_encrypted_db(path, key, **kw)`——给定 `key` 时返回带密钥的 SQLCipher 连接，否则返回
  普通 `sqlite3`（默认）。每个 SQLite 存储打开时经过的唯一接缝。
- `rbac.py` — RBAC/ABAC 引擎：`Role`/`ROLE_POLICIES`、`principal_for(User, Org)->Principal`、
  `authorize(Principal, action, ResourceRef)->Decision`（`rejected:rbac`）。与 §1.5 召回过滤器**同源**——复用
  `governance/rbac.py` 的 `Principal`/`scope_predicate`。

静态加密为可选启用（存储的 `cipher_key`/`cipher`；`CoreConfig.encryption_enabled` 是接缝，在组合根接线前失败即响）。
见 `../../../../docs/security/p0-1.9-threat-model-v1.md`。

**§1.6 — 注入防御（移植）：**
- `threat_patterns.py` — **移植**自 Hermes `tools/threat_patterns.py`（MIT）。3 范围模式库（`all` ⊂ `context` ⊂
  `strict`）+ `scan_for_threats(content, scope)` + `first_threat_message(content, scope)`（= §1.2 `scan_entry`
  接缝形态）+ `INVISIBLE_CHARS`。保留 `(?:\w+\s+)*` 多词绕过守卫与 C2 词汇锚定（非命令式英语）。记忆写入用 `strict`。
- `scrubber.py` — **移植**自 Hermes `StreamingContextScrubber`。跨块 `feed`/`flush`/`reset` 状态机，清洗跨流式 delta
  切分的 `<memory-context>` span；未关闭 span 在 `flush` 时丢弃。§1.3 围栏的流式对应物；真实流式模型路径为 §1.11。
- `external_ingest.py` — **新增**。`ingest_external_text(text, *, source, scope)`——外部文本的唯一入口：扫描 →
  命中威胁则阻断，否则用 §1.3 `<memory-context>` 围栏包裹。

压缩前事实注入接线（§1.6 另一交付物）位于 `core/compression.py`；真实 strict 扫描经
`memory/composition.build_memory_backend` 接入策展存储。
