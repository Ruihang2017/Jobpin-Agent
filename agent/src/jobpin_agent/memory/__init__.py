"""Memory Subsystem — curated + (later) entity memory.

EN —
Production Plan §1.2–1.6. This point (§1.2) ships the file-backed ``MemoryStore``:
the curated, low-volume, strongly-consistent layer (Org & Recruiter memory),
ported from Hermes. Later points add the ``MemoryProvider``/``MemoryManager``
orchestration (§1.3), the embedded vector store + entity providers (§1.4),
HR governance (§1.5), and injection defence (§1.6).

中文 —
生产计划 §1.2–1.6。本节点（§1.2）交付文件型 ``MemoryStore``：经人工策展、低频、强一致的层
（组织与招聘者记忆），移植自 Hermes。后续节点加入 ``MemoryProvider``/``MemoryManager`` 编排（§1.3）、
嵌入式向量库 + 实体 provider（§1.4）、HR 治理（§1.5）与注入防御（§1.6）。
"""
