# `docs/security/` — port security reviews

## English
Per-component security review records. Hermes is MIT and provided "as is" with no
warranty (PRD §2.7), so **every file we port from it gets its own security
review** before it is trusted in a regulated product; **net-new code in this
regulated product is reviewed too**. A checklist plus conclusions, named
`p<phase>-<point>-<slug>-review.md`. Not published.

- `p0-1.2-memory-store-port-review.md` — review of the §1.2 `MemoryStore` port.
- `p0-1.3-memory-provider-manager-review.md` — review of the §1.3 `MemoryProvider` + `MemoryManager` + fence port.
- `p0-1.4-vector-entity-providers-review.md` — review of the §1.4 vector store + Candidate/Semantic providers + minimal Composite.
- `p0-1.5-hr-memory-governance-review.md` — review of the §1.5 governance package (write-gate, bias hygiene, RBAC, erasure, audit) + the governed memory tool.
- `p0-1.6-injection-defence-review.md` — review of the §1.6 ports (threat_patterns + StreamingContextScrubber) + the external-ingest door + the compression fact-injection wiring.

## 中文
逐组件的安全评审记录。Hermes 为 MIT、"按原样"提供且无担保（PRD §2.7），故**我们从其移植的每个文件**在受监管
产品中被信任之前都要做自己的安全评审；**本受监管产品中的新增代码同样评审**。一份清单加结论，命名为
`p<phase>-<point>-<slug>-review.md`。不发布。

- `p0-1.2-memory-store-port-review.md` — §1.2 `MemoryStore` 移植的评审。
- `p0-1.3-memory-provider-manager-review.md` — §1.3 `MemoryProvider` + `MemoryManager` + 围栏 移植的评审。
- `p0-1.4-vector-entity-providers-review.md` — §1.4 向量库 + Candidate/Semantic provider + 最小 Composite 的评审。
- `p0-1.5-hr-memory-governance-review.md` — §1.5 治理包（写门控、偏见卫生、RBAC、擦除、审计）+ 受治理记忆工具的评审。
- `p0-1.6-injection-defence-review.md` — §1.6 移植（threat_patterns + StreamingContextScrubber）+ 外部 ingest 入口 + 压缩事实注入接线的评审。
