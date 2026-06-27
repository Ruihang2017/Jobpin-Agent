"""SQLite session store — durable conversation history with branch/reset.

EN —
Persists sessions and their messages to a single SQLite file (or ``:memory:``).
Supports resume (read a session back), branch (fork a session's history), and
reset (clear it) — the operations a long-running, resumable agent needs. Branch
and reset fire ``on_session_switch`` so the Memory Subsystem (§1.3+) can refresh
per-session caches. Messages (including tool calls/results) are JSON-serialised
so the round-trip is lossless. Design parallels Hermes session persistence.

中文 —
将会话及其消息持久化到单个 SQLite 文件（或 ``:memory:``）。支持 resume（读回会话）、branch（分叉会话历史）
与 reset（清空）——长时运行、可恢复的 agent 所需操作。branch 与 reset 触发 ``on_session_switch``，使
记忆子系统（§1.3+）可刷新按会话缓存。消息（含工具调用/结果）以 JSON 序列化，使往返无损。设计对应 Hermes
会话持久化。
"""
from __future__ import annotations

import json
import sqlite3
import uuid

from .hooks import MemoryHooks, NoOpHooks
from .messages import Message, Role, ToolCall, ToolResult


def _msg_to_dict(m: Message) -> dict:
    """Serialise a ``Message`` to a JSON-safe dict.

    EN: Args: m — the message. Returns: a dict with role/content/tool_calls/tool_result.
    中文：参数：m——消息。返回：含 role/content/tool_calls/tool_result 的 dict。
    """
    return {
        "role": m.role.value,
        "content": m.content,
        "tool_calls": [{"id": c.id, "name": c.name, "arguments": c.arguments} for c in m.tool_calls],
        "tool_result": (
            {"tool_call_id": m.tool_result.tool_call_id, "name": m.tool_result.name, "content": m.tool_result.content}
            if m.tool_result else None
        ),
    }


def _msg_from_dict(d: dict) -> Message:
    """Reconstruct a ``Message`` from its serialised dict.

    EN: Args: d — a dict from ``_msg_to_dict``. Returns: the rebuilt ``Message``.
    中文：参数：d——来自 ``_msg_to_dict`` 的 dict。返回：重建的 ``Message``。
    """
    return Message(
        role=Role(d["role"]),
        content=d.get("content", ""),
        tool_calls=[ToolCall(c["id"], c["name"], c["arguments"]) for c in d.get("tool_calls", [])],
        tool_result=(ToolResult(**d["tool_result"]) if d.get("tool_result") else None),
    )


class SessionStore:
    """Stores sessions and messages in SQLite.

    EN —
    Two tables: ``sessions`` (id, parent_id) and ``messages`` (session_id, seq,
    JSON payload). One store can hold many sessions (including delegated children
    linked by ``parent_id``).

    中文 —
    两张表：``sessions``（id、parent_id）与 ``messages``（session_id、seq、JSON 负载）。一个存储可容纳多个
    会话（包括经 ``parent_id`` 关联的委派子会话）。
    """

    def __init__(self, db_path: str = ":memory:", hooks: MemoryHooks | None = None) -> None:
        """Open (or create) the store and ensure the schema exists.

        EN —
        Args:
            db_path: SQLite path; ``:memory:`` for an ephemeral in-process DB.
            hooks: Memory hooks to notify on session switches (defaults to NoOp).

        中文 —
        参数：
            db_path：SQLite 路径；``:memory:`` 为进程内临时库。
            hooks：会话切换时通知的记忆钩子（默认 NoOp）。
        """
        self._conn = sqlite3.connect(db_path)
        self._hooks = hooks or NoOpHooks()
        self._conn.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, parent_id TEXT)")
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS messages "
            "(id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, seq INTEGER, payload TEXT)"
        )
        self._conn.commit()

    def create_session(self, session_id: str | None = None, parent_id: str | None = None) -> str:
        """Create a new session row.

        EN —
        Args:
            session_id: Explicit id (useful for tests/determinism); a random hex
                id is generated when ``None``.
            parent_id: The parent session id for delegated children (lineage), else ``None``.
        Returns:
            The session id.

        中文 —
        参数：
            session_id：显式 id（便于测试/确定性）；为 ``None`` 时生成随机十六进制 id。
            parent_id：委派子会话的父会话 id（血缘），否则为 ``None``。
        返回：
            会话 id。
        """
        sid = session_id or uuid.uuid4().hex
        self._conn.execute("INSERT INTO sessions (id, parent_id) VALUES (?, ?)", (sid, parent_id))
        self._conn.commit()
        return sid

    def _next_seq(self, session_id: str) -> int:
        """Compute the next message sequence number for a session.

        EN: Args: session_id. Returns: ``max(seq)+1`` (0 for an empty session).
        中文：参数：session_id。返回：``max(seq)+1``（空会话为 0）。
        """
        row = self._conn.execute(
            "SELECT COALESCE(MAX(seq), -1) FROM messages WHERE session_id=?", (session_id,)
        ).fetchone()
        return int(row[0]) + 1

    def append_message(self, session_id: str, message: Message) -> None:
        """Append a message to a session.

        EN —
        Args:
            session_id: Target session.
            message: The message to persist (serialised to JSON).

        中文 —
        参数：
            session_id：目标会话。
            message：要持久化的消息（序列化为 JSON）。
        """
        self._conn.execute(
            "INSERT INTO messages (session_id, seq, payload) VALUES (?, ?, ?)",
            (session_id, self._next_seq(session_id), json.dumps(_msg_to_dict(message))),
        )
        self._conn.commit()

    def get_messages(self, session_id: str) -> list[Message]:
        """Read a session's messages in order.

        EN —
        Args:
            session_id: The session to read.
        Returns:
            The messages ordered by ``seq`` (empty list if none).

        中文 —
        参数：
            session_id：要读取的会话。
        返回：
            按 ``seq`` 排序的消息（无则为空列表）。
        """
        rows = self._conn.execute(
            "SELECT payload FROM messages WHERE session_id=? ORDER BY seq", (session_id,)
        ).fetchall()
        return [_msg_from_dict(json.loads(r[0])) for r in rows]

    def branch(self, session_id: str, new_session_id: str | None = None) -> str:
        """Fork a session: copy its history into a new child session.

        EN —
        Args:
            session_id: Source session to fork.
            new_session_id: Optional explicit id for the new branch.
        Returns:
            The new session id. Fires ``on_session_switch(new, source, reset=False, rewound=False)``.

        中文 —
        参数：
            session_id：要分叉的源会话。
            new_session_id：新分支的可选显式 id。
        返回：
            新会话 id。触发 ``on_session_switch(new, source, reset=False, rewound=False)``。
        """
        new_id = self.create_session(new_session_id, parent_id=session_id)
        for m in self.get_messages(session_id):
            self.append_message(new_id, m)
        self._hooks.on_session_switch(new_id, session_id, False, False)
        return new_id

    def reset(self, session_id: str) -> None:
        """Clear all messages from a session (keeps the session row).

        EN —
        Args:
            session_id: The session to clear. Fires
                ``on_session_switch(session_id, None, reset=True, rewound=False)``.

        中文 —
        参数：
            session_id：要清空的会话。触发
                ``on_session_switch(session_id, None, reset=True, rewound=False)``。
        """
        self._conn.execute("DELETE FROM messages WHERE session_id=?", (session_id,))
        self._conn.commit()
        self._hooks.on_session_switch(session_id, None, True, False)
