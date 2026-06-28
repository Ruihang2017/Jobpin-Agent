"""The seam adapter — drives a ``MemoryManager`` through the §1.1 ``MemoryHooks``.

EN —
``MemoryManagerHooks`` is the linchpin of §1.3: it implements the §1.1
``core/hooks.py::MemoryHooks`` Protocol (duck-typed) by delegating to a
``MemoryManager``, so the whole memory backend attaches to the agent loop **with
no change to ``agent_loop.py``**. The §1.1 loop calls ``hooks.prefetch`` /
``after_turn`` / ``on_delegation`` / ``on_session_switch`` / ``on_pre_compress``;
this adapter translates those into the Manager's ``prefetch_all`` / ``sync_all`` +
``queue_prefetch_all`` / ``on_delegation`` / ``on_session_switch`` /
``on_pre_compress`` vocabulary.

Fence ownership: the §1.1 loop already wraps recall in the outer
``<memory-context>`` tags, so ``prefetch`` returns the INNER block
(``build_memory_context_inner``) — the loop's wrapping reproduces Hermes's full
block byte-for-byte.

中文 —
``MemoryManagerHooks`` 是 §1.3 的关键：它通过委派给 ``MemoryManager`` 来实现 §1.1
``core/hooks.py::MemoryHooks`` 协议（鸭子类型），使整个记忆后端**在不改动 ``agent_loop.py``** 的前提下接入
agent 循环。§1.1 循环调用 ``hooks.prefetch`` / ``after_turn`` / ``on_delegation`` / ``on_session_switch`` /
``on_pre_compress``；本适配器将其转译为 Manager 的 ``prefetch_all`` / ``sync_all`` + ``queue_prefetch_all`` /
``on_delegation`` / ``on_session_switch`` / ``on_pre_compress`` 词汇。

围栏归属：§1.1 循环已用外层 ``<memory-context>`` 标签包裹召回，故 ``prefetch`` 返回 INNER 块
（``build_memory_context_inner``）——循环的包裹复现 Hermes 完整块且逐字节一致。
"""
from __future__ import annotations

from typing import Any, Dict, List

from ..core.messages import Message, Role
from .fence import build_memory_context_inner
from .manager import MemoryManager


def _last_text(messages: List[Message], role: Role) -> str:
    """Return the last message's content for a given role, or ``""``.

    EN: Args: messages; role. Returns: the most recent ``content`` for that role.
    中文：参数：messages；role。返回：该角色最近一条的 ``content``。
    """
    for m in reversed(messages):
        if m.role == role and m.content:
            return m.content
    return ""


def _as_dicts(messages: List[Message]) -> List[Dict[str, Any]]:
    """Render §1.1 ``Message`` objects as OpenAI-style dicts for the provider contract.

    EN —
    Providers' ``sync_turn(..., messages=...)`` and ``on_pre_compress(messages)``
    expect the wire-style list (role + content/tool_calls/tool_result).
    Args: messages. Returns: a list of JSON-safe dicts.

    中文 —
    provider 的 ``sync_turn(..., messages=...)`` 与 ``on_pre_compress(messages)`` 期望线格式列表
    （role + content/tool_calls/tool_result）。参数：messages。返回：JSON 安全的字典列表。
    """
    out: List[Dict[str, Any]] = []
    for m in messages:
        d: Dict[str, Any] = {"role": m.role.value, "content": m.content}
        if m.tool_calls:
            d["tool_calls"] = [{"id": c.id, "name": c.name, "arguments": c.arguments} for c in m.tool_calls]
        if m.tool_result is not None:
            d["tool_result"] = {
                "tool_call_id": m.tool_result.tool_call_id,
                "name": m.tool_result.name,
                "content": m.tool_result.content,
            }
        out.append(d)
    return out


class MemoryManagerHooks:
    """Implements the §1.1 ``MemoryHooks`` Protocol over a ``MemoryManager``.

    EN —
    Duck-typed against ``core.hooks.MemoryHooks`` (no subclassing needed). Pass an
    instance as ``Agent(..., hooks=...)`` and the backend's recall/sync lifecycle
    runs with no loop change. ``after_turn`` dispatches sync + next-turn prefetch to
    the Manager's background worker (non-blocking); tests/boundaries use
    ``manager.flush_pending`` to make persistence visible.

    中文 —
    对 ``core.hooks.MemoryHooks`` 鸭子类型实现（无需继承）。将其实例作为 ``Agent(..., hooks=...)`` 传入，
    后端的召回/同步生命周期即可在不改动循环的前提下运行。``after_turn`` 把 sync 与下一回合 prefetch 派发给
    Manager 的后台工作线程（非阻塞）；测试/边界用 ``manager.flush_pending`` 使持久化可见。
    """

    def __init__(self, manager: MemoryManager) -> None:
        """Wrap a manager.

        EN: Args: manager — the assembled ``MemoryManager``.
        中文：参数：manager——已装配的 ``MemoryManager``。
        """
        self._manager = manager

    def prefetch(self, query: str, session_id: str) -> str:
        """Pre-turn recall as the INNER fenced block (the loop adds the outer tags).

        EN: Args: query; session_id. Returns: ``build_memory_context_inner`` of the merged recall, or ``""``.
        中文：参数：query；session_id。返回：合并召回的 ``build_memory_context_inner``，或 ``""``。
        """
        return build_memory_context_inner(self._manager.prefetch_all(query, session_id=session_id))

    def after_turn(self, session_id: str, messages: List[Message]) -> None:
        """Persist the turn + warm the next prefetch (both on the background worker).

        EN: Args: session_id; messages (the full post-turn history). Returns: None (non-blocking).
        中文：参数：session_id；messages（回合后完整历史）。返回：None（非阻塞）。
        """
        user = _last_text(messages, Role.USER)
        assistant = _last_text(messages, Role.ASSISTANT)
        self._manager.sync_all(user, assistant, session_id=session_id, messages=_as_dicts(messages))
        self._manager.queue_prefetch_all(user, session_id=session_id)

    def on_delegation(self, task: str, result: str, child_session_id: str) -> None:
        """Forward a subagent completion to the providers (parent-side observation).

        EN: Args: task; result; child_session_id. Returns: None.
        中文：参数：task；result；child_session_id。返回：None。
        """
        self._manager.on_delegation(task, result, child_session_id=child_session_id)

    def on_session_switch(self, new_session_id: str, parent_session_id: str | None, reset: bool, rewound: bool) -> None:
        """Forward a session-id rotation to the providers.

        EN: Args: new_session_id; parent_session_id; reset; rewound. Returns: None.
        中文：参数：new_session_id；parent_session_id；reset；rewound。返回：None。
        """
        self._manager.on_session_switch(
            new_session_id, parent_session_id=parent_session_id or "", reset=reset, rewound=rewound
        )

    def on_pre_compress(self, messages: List[Message]) -> str:
        """Aggregate providers' pre-compression facts (the §1.6 wiring captures this).

        EN: Args: messages. Returns: the joined facts to retain, or ``""``.
        中文：参数：messages。返回：要保留的连接事实，或 ``""``。
        """
        return self._manager.on_pre_compress(_as_dicts(messages))
