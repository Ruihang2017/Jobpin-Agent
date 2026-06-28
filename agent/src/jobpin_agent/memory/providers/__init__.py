"""Concrete memory providers (the package §1.4 extends).

EN —
Holds implementations of the ``MemoryProvider`` contract. §1.3 ships only the
``builtin`` provider (wrapping the §1.2 file-backed ``MemoryStore``). §1.4 adds the
large-volume retrieval providers (candidate / semantic) over the embedded vector
store; §1.5 adds the governed write tool to the built-in provider.

中文 —
存放 ``MemoryProvider`` 契约的实现。§1.3 仅交付 ``builtin`` provider（包裹 §1.2 文件型 ``MemoryStore``）。
§1.4 在嵌入式向量库上新增大体量检索 provider（候选 / 语义）；§1.5 为内置 provider 加入受治理的写工具。
"""
