# Entity ↔ Memory Mapping (§1.8 deliverable)

Which canonical entity fields live in which store, and how the `MemoryRecord` seam table indexes them.
This is the §1.8 deliverable that ties the canonical relational model (`data/`) to the memory subsystem
(`memory/`) and the governance labels (`governance/`).

## English

### The three stores
| Store | Module | Holds | Source of truth? |
|---|---|---|---|
| **Relational (canonical)** | `data/` (§1.8) | the full canonical entities (Candidate / Job / Application / Interview / Consent / Org / User) + the `audit_log` + `memory_record` seam | **Yes** — the authoritative record of *what we hold about a person* |
| **Structured (retrieval)** | `memory/structured.py` (§1.4) | a *minimal projection* of candidate filter fields (skills / years / location / work_rights / consent_status), keyed by `memory_key` | No — a **projection** of the canonical Candidate, scoped to fast filter-before-NN recall |
| **Vector** | `memory/vector/` (§1.4) | the semantic vectors of résumé/JD chunks + back-references (`memory_key`, `source_ref`) | No — derived embeddings; the text/labels live elsewhere |
| **File-backed (curated)** | `memory/store.py` (§1.2) | hand-curated Org / Recruiter memory (ORG.md / RECRUITER.md), each entry carrying the §1.5 governance header | Yes for *curated* org/recruiter facts (not entity rows) |

### Candidate field → store
| Canonical `Candidate` field | Relational (canonical) | Structured (§1.4) | Vector (§1.4) | File (§1.2) |
|---|---|---|---|---|
| `candidate_id`, `tenant_id`, `org_id` | ✅ source of truth | — | — | — |
| `name`, `years`, `location`, `work_rights` | ✅ | ✅ projection (filter) | — | — |
| `skills[]` | ✅ | ✅ projection (filter) | — | — |
| `consent_status` | ✅ | ✅ projection (the §1.5 ingest gate reads it) | — | — |
| `memory_key` | ✅ (links to `memory_record` + the §1.4 stores) | ✅ (the key) | ✅ (`VectorRecord.memory_key`) | — |
| résumé free text / chunks | — | — | ✅ vectors + `source_ref` | — |
| org hiring rubric / recruiter "bar" | — | — | (semantic, if ingested) | ✅ curated |

### The `MemoryRecord` seam
`MemoryRecord := { memory_key, store_kind ∈ {file, vector, struct}, provenance, consent_label, retention_policy }`
is the relational **index** of every memory entry across the three stores: given a `memory_key`, it says
which store holds it and carries the §1.5 governance labels (provenance / lawful-basis / retention). A
data-subject query ("what do we hold about `cand_7f3a`, where, under what lawful basis?") is backed by
`CanonicalStore.consents_for_candidate(candidate_id)` (`Candidate → Consent`) +
`CanonicalStore.memory_records_under(prefix)` (`Candidate → MemoryRecord` by `memory_key` prefix, matching
the exact key + colon-nested keys) → the audit log; an erasure (§1.5) deletes across the stores and records
the `erase` in the canonical audit. (`MemoryRecord` PK = `memory_key`, so one row per key — a key held in
two stores at once is represented once today; a per-(key, store_kind) row is a future refinement.)

### Honest boundary
The canonical `Candidate` and the §1.4 structured projection are **written separately by the caller today**
— there is no automatic sync/trigger yet (a sync lands when M3 wires the real ingest pipeline). The
canonical store is the source of truth; the §1.4 projection is a denormalised copy for fast recall.

## 中文

### 三个存储
| 存储 | 模块 | 持有 | 是否事实来源 |
|---|---|---|---|
| **关系（规范）** | `data/`（§1.8） | 完整规范实体（Candidate / Job / Application / Interview / Consent / Org / User）+ `audit_log` + `memory_record` 接缝 | **是**——*关于某人我们持有什么*的权威记录 |
| **结构化（检索）** | `memory/structured.py`（§1.4） | 候选人过滤字段的*最小投影*（技能/年限/地点/工作权利/同意），以 `memory_key` 为键 | 否——规范 Candidate 的**投影**，为快速“先过滤再近邻”召回 |
| **向量** | `memory/vector/`（§1.4） | 简历/JD 片段的语义向量 + 回指（`memory_key`、`source_ref`） | 否——派生嵌入；文本/标签在别处 |
| **文件型（策展）** | `memory/store.py`（§1.2） | 人工策展的 Org / Recruiter 记忆（ORG.md / RECRUITER.md），每条带 §1.5 治理头 | 对*策展*组织/招聘官事实为是（非实体行） |

### Candidate 字段 → 存储
| 规范 `Candidate` 字段 | 关系（规范） | 结构化（§1.4） | 向量（§1.4） | 文件（§1.2） |
|---|---|---|---|---|
| `candidate_id`、`tenant_id`、`org_id` | ✅ 事实来源 | — | — | — |
| `name`、`years`、`location`、`work_rights` | ✅ | ✅ 投影（过滤） | — | — |
| `skills[]` | ✅ | ✅ 投影（过滤） | — | — |
| `consent_status` | ✅ | ✅ 投影（§1.5 ingest 门控读取） | — | — |
| `memory_key` | ✅（链接 `memory_record` + §1.4 存储） | ✅（键） | ✅（`VectorRecord.memory_key`） | — |
| 简历自由文本 / 片段 | — | — | ✅ 向量 + `source_ref` | — |
| 组织招聘细则 / 招聘官“标尺” | — | — | （语义，若 ingest） | ✅ 策展 |

### `MemoryRecord` 接缝
`MemoryRecord := { memory_key, store_kind ∈ {file, vector, struct}, provenance, consent_label, retention_policy }`
是跨三个存储的每条记忆条目的关系**索引**：给定 `memory_key`，它指明哪个存储持有它，并携带 §1.5 治理标签（来源/合法依据/
留存）。数据主体查询（”关于 `cand_7f3a` 我们持有什么、在哪、依何合法依据？”）由 `CanonicalStore.consents_for_candidate`
（`Candidate → Consent`）+ `CanonicalStore.memory_records_under(prefix)`（`Candidate → MemoryRecord` 按 `memory_key`
前缀，匹配精确键 + 冒号嵌套键）→ 审计日志 支撑；擦除（§1.5）跨存储删除并把 `erase` 记入规范审计。（`MemoryRecord` 主键 =
`memory_key`，故每键一行——同时存于两个存储的键当前只表示一次；按 (key, store_kind) 一行为未来细化。）

### 诚实边界
规范 `Candidate` 与 §1.4 结构化投影**当前由调用方分别写入**——尚无自动同步/触发器（同步在 M3 接入真实 ingest 流水线时
落地）。规范存储是事实来源；§1.4 投影是为快速召回的去规范化副本。
