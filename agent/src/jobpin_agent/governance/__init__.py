"""HR memory governance (§1.5) — the compliance shell around the memory subsystem.

EN —
Net-new to the project (Hermes lacks this); the linchpin of Australian compliance. This package wraps
every memory write and recall in a governance shell — namespace + provenance + lawful-basis / consent
labels + retention + RBAC + audit + bias hygiene — so the system moves from "can remember" to
"remembers compliantly, uses explainably, and can be erased" (PRD §9.5; Production Plan §1.5).

It is consumed by the existing memory paths rather than replacing them: governance is enforced in the
governed write tool's write path AND the entity-ingest path (the writers, so the ported ``MemoryStore``
stays unchanged) and on the recall path via the existing filter-before-NN ``scope`` seam; erasure
orchestrates the §1.4 ``delete_by_key_prefix`` cascade; audit is an append-only local log.

Honest boundaries (stated truthfully, not overclaimed): "can be erased" means **live-store** deletion
+ cache clear + a backup-ageing register entry — backups age out per retention, NOT a GDPR-instant wipe,
and de-identification of residual mentions in *other* entries is the §1.11 pipeline. The bias scanner is
a curated heuristic, not a complete classifier. The §1.5 audit covers the write + erase paths; the read
(recall) trail is deferred to §1.8 (the thread-safe canonical audit table). RBAC's auth source is
injected/deferred (PRD open-Q#8).

中文 —
本项目新增（Hermes 缺失）；澳大利亚合规的关键。本包把每次记忆写入与召回包裹进治理外壳——命名空间 + 来源 +
合法依据/同意标签 + 留存 + RBAC + 审计 + 偏见卫生——使系统从“能记住”升级为“合规地记住、可解释地使用、可被擦除”
（PRD §9.5；生产计划 §1.5）。

它被既有记忆路径消费而非替换：治理在受治理写工具的写路径与实体 ingest 路径上强制（即写入者，故移植的 ``MemoryStore``
保持不变），并经既有的“先过滤再近邻”``scope`` 接缝作用于召回路径；擦除编排 §1.4 的 ``delete_by_key_prefix`` 级联；
审计为仅追加的本地日志。

诚实边界（如实陈述，不夸大）：“可被擦除”指**实时存储**删除 + 缓存清空 + 一条备份老化登记——备份按留存期老化，并非
GDPR 式即时清除，且对*其他*条目中残留提及的去标识化属于 §1.11 流水线。偏见扫描器是策展启发式，并非完整分类器。
§1.5 审计覆盖写 + 擦除路径；读（召回）痕迹推迟到 §1.8（线程安全的规范审计表）。RBAC 的鉴权来源注入/推迟（PRD 开放问题 #8）。
"""
