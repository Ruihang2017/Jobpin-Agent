"""HR memory governance (§1.5) — the compliance shell around the memory subsystem.

EN —
Net-new to the project (Hermes lacks this); the linchpin of Australian compliance. This package wraps
every memory write and recall in a governance shell — namespace + provenance + lawful-basis / consent
labels + retention + RBAC + audit + bias hygiene — so the system moves from "can remember" to
"remembers compliantly, uses explainably, and can be erased" (PRD §9.5; Production Plan §1.5).

It is consumed by the existing memory paths rather than replacing them: governance is enforced in the
governed write tool's write path (the sole writer to the curated store, so the ported ``MemoryStore``
stays unchanged) and on the recall path via the existing filter-before-NN ``scope`` seam; erasure
orchestrates the §1.4 ``delete_by_key_prefix`` cascade; audit is an append-only local log.

中文 —
本项目新增（Hermes 缺失）；澳大利亚合规的关键。本包把每次记忆写入与召回包裹进治理外壳——命名空间 + 来源 +
合法依据/同意标签 + 留存 + RBAC + 审计 + 偏见卫生——使系统从“能记住”升级为“合规地记住、可解释地使用、可被擦除”
（PRD §9.5；生产计划 §1.5）。

它被既有记忆路径消费而非替换：治理在受治理写工具的写路径上强制（策展存储的唯一写入者，故移植的 ``MemoryStore``
保持不变），并经既有的“先过滤再近邻”``scope`` 接缝作用于召回路径；擦除编排 §1.4 的 ``delete_by_key_prefix`` 级联；
审计为仅追加的本地日志。
"""
