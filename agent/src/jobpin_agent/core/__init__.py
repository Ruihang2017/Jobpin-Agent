"""Agent Core (Layer A) — the local, provider-agnostic agent runtime.

EN —
This package holds Production Plan §1.1: the lean conversation loop, deterministic
system-prompt assembly, sub-agent delegation, a SQLite session store, the
provider-agnostic model layer (under ``model/``), step-level tracing, and the
no-op ``MemoryHooks`` seam that the Memory Subsystem (§1.2–1.6) attaches to.
Nothing here depends on a specific LLM vendor or on the Hermes runtime; design
was borrowed from Hermes and rewritten for clean ownership (PRD §2.7).

中文 —
本包对应生产计划 §1.1：精简会话循环、确定性系统提示装配、子代理委派、SQLite 会话存储、
provider 无关的模型层（位于 ``model/``）、步骤级追踪，以及记忆子系统（§1.2–1.6）后续接入的
空操作 ``MemoryHooks`` 接缝。此处任何代码都不依赖特定 LLM 厂商或 Hermes 运行时；设计借鉴自
Hermes 并重写以获得干净所有权（PRD §2.7）。
"""
