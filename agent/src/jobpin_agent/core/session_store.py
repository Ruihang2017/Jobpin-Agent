"""SQLite-backed session store (single file). Supports resume/branch/reset,
firing on_session_switch. Design parallels Hermes session persistence."""
from __future__ import annotations

import json
import sqlite3
import uuid

from .hooks import MemoryHooks, NoOpHooks
from .messages import Message, Role, ToolCall, ToolResult


def _msg_to_dict(m: Message) -> dict:
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
    return Message(
        role=Role(d["role"]),
        content=d.get("content", ""),
        tool_calls=[ToolCall(c["id"], c["name"], c["arguments"]) for c in d.get("tool_calls", [])],
        tool_result=(ToolResult(**d["tool_result"]) if d.get("tool_result") else None),
    )


class SessionStore:
    def __init__(self, db_path: str = ":memory:", hooks: MemoryHooks | None = None) -> None:
        self._conn = sqlite3.connect(db_path)
        self._hooks = hooks or NoOpHooks()
        self._conn.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, parent_id TEXT)")
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS messages "
            "(id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, seq INTEGER, payload TEXT)"
        )
        self._conn.commit()

    def create_session(self, session_id: str | None = None, parent_id: str | None = None) -> str:
        sid = session_id or uuid.uuid4().hex
        self._conn.execute("INSERT INTO sessions (id, parent_id) VALUES (?, ?)", (sid, parent_id))
        self._conn.commit()
        return sid

    def _next_seq(self, session_id: str) -> int:
        row = self._conn.execute(
            "SELECT COALESCE(MAX(seq), -1) FROM messages WHERE session_id=?", (session_id,)
        ).fetchone()
        return int(row[0]) + 1

    def append_message(self, session_id: str, message: Message) -> None:
        self._conn.execute(
            "INSERT INTO messages (session_id, seq, payload) VALUES (?, ?, ?)",
            (session_id, self._next_seq(session_id), json.dumps(_msg_to_dict(message))),
        )
        self._conn.commit()

    def get_messages(self, session_id: str) -> list[Message]:
        rows = self._conn.execute(
            "SELECT payload FROM messages WHERE session_id=? ORDER BY seq", (session_id,)
        ).fetchall()
        return [_msg_from_dict(json.loads(r[0])) for r in rows]

    def branch(self, session_id: str, new_session_id: str | None = None) -> str:
        new_id = self.create_session(new_session_id, parent_id=session_id)
        for m in self.get_messages(session_id):
            self.append_message(new_id, m)
        self._hooks.on_session_switch(new_id, session_id, False, False)
        return new_id

    def reset(self, session_id: str) -> None:
        self._conn.execute("DELETE FROM messages WHERE session_id=?", (session_id,))
        self._conn.commit()
        self._hooks.on_session_switch(session_id, None, True, False)
