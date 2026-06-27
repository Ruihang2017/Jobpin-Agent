"""The memory seam — where the Memory Subsystem attaches without touching the loop.

EN —
``MemoryHooks`` is the contract the agent loop calls at well-defined moments
(before a turn, after a turn, on delegation, on session switch, before context
compression). In §1.1 we ship only ``NoOpHooks`` (everything inert), so the loop
runs with no memory. §1.2–1.6 implement real hooks — file-backed ``MemoryStore``,
entity providers, governance — and plug them in *without changing*
``agent_loop.py``. The hook set mirrors the Hermes ``MemoryProvider`` lifecycle so
the port maps cleanly.

中文 —
``MemoryHooks`` 是 agent 循环在明确时机调用的契约（回合前、回合后、委派时、会话切换时、上下文压缩前）。
§1.1 仅提供 ``NoOpHooks``（全部空操作），使循环在无记忆下运行。§1.2–1.6 实现真实钩子——文件型
``MemoryStore``、实体 provider、治理——并在*不改动* ``agent_loop.py`` 的前提下接入。钩子集合对应
Hermes ``MemoryProvider`` 生命周期，使移植映射干净。
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from .messages import Message


@runtime_checkable
class MemoryHooks(Protocol):
    """Structural contract for memory integration points.

    EN —
    A ``Protocol`` (duck-typed): any object with these methods qualifies, so
    later memory implementations need not import or subclass this. Marked
    ``runtime_checkable`` so ``isinstance`` works in tests.

    Methods:
        prefetch(query, session_id) -> str: Recall relevant memory before a turn;
            the loop injects the result as a fenced ``<memory-context>`` message.
        after_turn(session_id, messages) -> None: Persist after a turn completes.
        on_delegation(task, result, child_session_id) -> None: Let the parent
            observe a sub-agent's result and adjudicate any memory writes.
        on_session_switch(new, parent, reset, rewound) -> None: React to
            resume/branch/reset boundaries.
        on_pre_compress(messages) -> str: Return key facts to retain before the
            context is compressed (wiring is §1.6).

    中文 —
    一个 ``Protocol``（鸭子类型）：任何具备这些方法的对象都符合，故后续记忆实现无需导入或继承本类。
    标注 ``runtime_checkable`` 以便测试中可用 ``isinstance``。

    方法：
        prefetch(query, session_id) -> str：回合前召回相关记忆；循环将结果作为围栏
            ``<memory-context>`` 消息注入。
        after_turn(session_id, messages) -> None：回合完成后持久化。
        on_delegation(task, result, child_session_id) -> None：让父代理观察子代理结果并审定记忆写入。
        on_session_switch(new, parent, reset, rewound) -> None：响应 resume/branch/reset 边界。
        on_pre_compress(messages) -> str：在上下文压缩前返回应保留的关键事实（接线在 §1.6）。
    """

    def prefetch(self, query: str, session_id: str) -> str: ...
    def after_turn(self, session_id: str, messages: list[Message]) -> None: ...
    def on_delegation(self, task: str, result: str, child_session_id: str) -> None: ...
    def on_session_switch(self, new_session_id: str, parent_session_id: str | None, reset: bool, rewound: bool) -> None: ...
    def on_pre_compress(self, messages: list[Message]) -> str: ...


class NoOpHooks:
    """The §1.1 implementation: every hook is inert.

    EN —
    Lets the agent core run end-to-end with no memory. ``prefetch`` and
    ``on_pre_compress`` return ``""``; the rest return ``None``. §1.2+ replace
    this with real behaviour behind the same interface.

    中文 —
    使 agent 内核在无记忆下端到端运行。``prefetch`` 与 ``on_pre_compress`` 返回 ``""``；其余返回
    ``None``。§1.2+ 在同一接口下以真实行为替换。
    """

    def prefetch(self, query: str, session_id: str) -> str:
        """No recall in §1.1.

        EN: Args: query, session_id (ignored). Returns: empty string.
        中文：参数：query、session_id（忽略）。返回：空字符串。
        """
        return ""

    def after_turn(self, session_id: str, messages: list[Message]) -> None:
        """No persistence in §1.1.

        EN: Args: session_id, messages (ignored). Returns: None.
        中文：参数：session_id、messages（忽略）。返回：None。
        """
        return None

    def on_delegation(self, task: str, result: str, child_session_id: str) -> None:
        """No parent adjudication in §1.1.

        EN: Args: task, result, child_session_id (ignored). Returns: None.
        中文：参数：task、result、child_session_id（忽略）。返回：None。
        """
        return None

    def on_session_switch(self, new_session_id: str, parent_session_id: str | None, reset: bool, rewound: bool) -> None:
        """No reaction to session switches in §1.1.

        EN: Args: new/parent session ids, reset, rewound (ignored). Returns: None.
        中文：参数：新/父会话 id、reset、rewound（忽略）。返回：None。
        """
        return None

    def on_pre_compress(self, messages: list[Message]) -> str:
        """No pre-compression fact extraction in §1.1 (seam only; wiring is §1.6).

        EN: Args: messages (ignored). Returns: empty string.
        中文：参数：messages（忽略）。返回：空字符串。
        """
        return ""
