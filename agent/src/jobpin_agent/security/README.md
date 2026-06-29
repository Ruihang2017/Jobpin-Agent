# `security/` — Context-window security (§1.6)

## English
The product's injection-defence layer (Production Plan §1.6; PRD §2.7 — "port the code" for injection
defence). Résumés, emails, and JDs are untrusted input and a real prompt-injection surface, so external
text is scanned and fenced before it reaches the model's context or memory. The threat library and the
streaming scrubber are **ported from Hermes (MIT)** — see `../../../THIRD_PARTY_NOTICES.md`.

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
产品的注入防御层（生产计划 §1.6；PRD §2.7——注入防御“移植代码”）。简历、邮件与 JD 是不可信输入且为真实提示注入面，
故外部文本在进入模型上下文或记忆前被扫描与围栏。威胁库与流式清洗器**移植自 Hermes（MIT）**——见
`../../../THIRD_PARTY_NOTICES.md`。

- `threat_patterns.py` — **移植**自 Hermes `tools/threat_patterns.py`（MIT）。3 范围模式库（`all` ⊂ `context` ⊂
  `strict`）+ `scan_for_threats(content, scope)` + `first_threat_message(content, scope)`（= §1.2 `scan_entry`
  接缝形态）+ `INVISIBLE_CHARS`。保留 `(?:\w+\s+)*` 多词绕过守卫与 C2 词汇锚定（非命令式英语）。记忆写入用 `strict`。
- `scrubber.py` — **移植**自 Hermes `StreamingContextScrubber`。跨块 `feed`/`flush`/`reset` 状态机，清洗跨流式 delta
  切分的 `<memory-context>` span；未关闭 span 在 `flush` 时丢弃。§1.3 围栏的流式对应物；真实流式模型路径为 §1.11。
- `external_ingest.py` — **新增**。`ingest_external_text(text, *, source, scope)`——外部文本的唯一入口：扫描 →
  命中威胁则阻断，否则用 §1.3 `<memory-context>` 围栏包裹。

压缩前事实注入接线（§1.6 另一交付物）位于 `core/compression.py`；真实 strict 扫描经
`memory/composition.build_memory_backend` 接入策展存储。
