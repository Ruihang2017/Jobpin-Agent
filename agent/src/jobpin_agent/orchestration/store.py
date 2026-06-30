"""SQLite persistence for the Layer B state machine (§1.7).

EN —
The durable store behind the orchestration engine — the load anchor for crash recovery. Three tables in
one local SQLite file (consistent with ``SessionStore`` / the §1.4 stores / the §1.5 audit log):
``process_instances`` (one row per instance, upserted), ``transitions`` (append-only, the auditable state
history — no update/delete API), and ``idempotency`` (external side-effect dedup). All SQL is
parameterised. A fresh store over the **same file** sees committed data — that is how a "restart" recovers.

中文 —
编排引擎背后的持久化存储——崩溃恢复的加载锚点。一个本地 SQLite 文件中三张表（与 ``SessionStore`` / §1.4 存储 / §1.5
审计日志一致）：``process_instances``（每实例一行，upsert）、``transitions``（仅追加，可审计状态历史——无更新/删除 API）、
``idempotency``（外部副作用去重）。所有 SQL 参数化。在**同一文件**上新建存储即可见已提交数据——“重启”据此恢复。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Optional

from .state_machine import ProcessInstance, Status, Transition


class OrchestrationStore:
    """SQLite store for process instances, the append-only transition history, and idempotency keys.

    EN —
    Construct over ``:memory:`` (ephemeral) or a file path (durable — required for the restart/recovery
    tests). The transition table is append-only by construction (no mutation method).

    中文 —
    在 ``:memory:``（临时）或文件路径（持久——重启/恢复测试需要）上构造。转移表按构造即仅追加（无修改方法）。
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        """Open (or create) the store and ensure the three tables.

        EN: Args: db_path (``:memory:`` or a file path). 中文：参数：db_path（``:memory:`` 或文件路径）。
        """
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS process_instances ("
            "instance_id TEXT PRIMARY KEY, process_type TEXT, current_state TEXT, status TEXT, "
            "context_ref TEXT, updated_at TEXT)"
        )
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS transitions ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, instance_id TEXT, from_state TEXT, to_state TEXT, "
            "trigger TEXT, at TEXT, actor TEXT)"
        )
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS idempotency ("
            "key TEXT PRIMARY KEY, status TEXT, result TEXT, at TEXT)"
        )
        self._conn.commit()

    def save_instance(self, inst: ProcessInstance) -> None:
        """Upsert a process instance (the recovery load anchor).

        EN: Args: inst. Returns: None. 中文：参数：inst。返回：None。
        """
        self._conn.execute(
            "INSERT OR REPLACE INTO process_instances VALUES (?, ?, ?, ?, ?, ?)",
            (inst.instance_id, inst.process_type, inst.current_state, inst.status.value,
             inst.context_ref, inst.updated_at),
        )
        self._conn.commit()

    def load_instance(self, instance_id: str) -> Optional[ProcessInstance]:
        """Load a process instance by id.

        EN: Args: instance_id. Returns: the ``ProcessInstance``, or None. 中文：参数：instance_id。返回：``ProcessInstance`` 或 None。
        """
        row = self._conn.execute(
            "SELECT instance_id, process_type, current_state, status, context_ref, updated_at "
            "FROM process_instances WHERE instance_id=?", (instance_id,)
        ).fetchone()
        if row is None:
            return None
        return ProcessInstance(row[0], row[1], row[2], Status(row[3]), context_ref=row[4], updated_at=row[5])

    def append_transition(self, t: Transition) -> None:
        """Append a transition to the auditable history (append-only).

        EN: Args: t. Returns: None. 中文：参数：t。返回：None。
        """
        self._conn.execute(
            "INSERT INTO transitions (instance_id, from_state, to_state, trigger, at, actor) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (t.instance_id, t.from_state, t.to_state, t.trigger, t.at, t.actor),
        )
        self._conn.commit()

    def apply(self, inst: ProcessInstance, transition: Transition) -> None:
        """Upsert the instance AND append its transition in ONE transaction (atomic) — §1.7 M1 fix.

        EN —
        The engine's state advance and its audit record must commit together: a crash between two separate
        commits would leave ``current_state`` advanced with no transition explaining it, silently breaking
        the append-only audit chain (the triple-review M1). Both writes share one implicit SQLite
        transaction, committed once — so a recovered instance's state and its history can never diverge.
        (Mirrors ``core/session_store.py::compact``'s single-commit pattern.) Args: inst; transition. Returns: None.

        中文 —
        引擎的状态推进与其审计记录必须一起提交：两次独立提交之间崩溃会使 ``current_state`` 推进却无解释它的转移，悄然
        破坏仅追加审计链（三方评审 M1）。两次写入共享一个隐式 SQLite 事务、提交一次——故恢复实例的状态与历史绝不背离。
        （对应 ``core/session_store.py::compact`` 的单次提交。）参数：inst；transition。返回：None。
        """
        self._conn.execute(
            "INSERT OR REPLACE INTO process_instances VALUES (?, ?, ?, ?, ?, ?)",
            (inst.instance_id, inst.process_type, inst.current_state, inst.status.value,
             inst.context_ref, inst.updated_at),
        )
        self._conn.execute(
            "INSERT INTO transitions (instance_id, from_state, to_state, trigger, at, actor) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (transition.instance_id, transition.from_state, transition.to_state,
             transition.trigger, transition.at, transition.actor),
        )
        self._conn.commit()  # single commit → instance + transition land atomically

    def transitions_for(self, instance_id: str) -> List[Transition]:
        """Read an instance's transition history in order.

        EN: Args: instance_id. Returns: the transitions, oldest first. 中文：参数：instance_id。返回：转移，最早在前。
        """
        rows = self._conn.execute(
            "SELECT instance_id, from_state, to_state, trigger, at, actor FROM transitions "
            "WHERE instance_id=? ORDER BY id", (instance_id,)
        ).fetchall()
        return [Transition(*row) for row in rows]

    def non_terminal_instances(self) -> List[ProcessInstance]:
        """Return all instances not in a terminal status (for crash recovery).

        EN: Returns: instances with status RUNNING / SUSPENDED / AWAITING_HITL.
        中文：返回：状态为 RUNNING / SUSPENDED / AWAITING_HITL 的实例。
        """
        rows = self._conn.execute(
            "SELECT instance_id FROM process_instances WHERE status IN (?, ?, ?)",
            (Status.RUNNING.value, Status.SUSPENDED.value, Status.AWAITING_HITL.value),
        ).fetchall()
        return [self.load_instance(r[0]) for r in rows]

    def idem_get(self, key: str) -> Optional[dict]:
        """Look up an idempotency key.

        EN: Args: key. Returns: ``{"status", "result"}`` or None. 中文：参数：key。返回：``{"status", "result"}`` 或 None。
        """
        row = self._conn.execute("SELECT status, result FROM idempotency WHERE key=?", (key,)).fetchone()
        return None if row is None else {"status": row[0], "result": row[1]}

    def idem_put(self, key: str, status: str, result: str, at: str = "") -> None:
        """Upsert an idempotency key (``pending`` then ``done``).

        EN: Args: key; status; result; at. Returns: None. 中文：参数：key；status；result；at。返回：None。
        """
        self._conn.execute("INSERT OR REPLACE INTO idempotency VALUES (?, ?, ?, ?)", (key, status, result, at))
        self._conn.commit()

    def idem_begin(self, key: str, at: str = "") -> bool:
        """Atomically claim a key as ``pending`` via a plain INSERT — returns False if already claimed.

        EN —
        Race-safe registration (the triple-review M2 fix): a plain ``INSERT`` relies on the ``key`` PRIMARY
        KEY, so exactly one racer wins; a concurrent (or replayed) claim raises ``IntegrityError`` and
        returns False. Unlike ``idem_put`` (``INSERT OR REPLACE``), this does NOT overwrite an existing
        claim, so "never double-execute" holds even across processes. Args: key; at. Returns: True if newly
        claimed, False if the key already exists.

        中文 —
        竞态安全登记（三方评审 M2 修复）：纯 ``INSERT`` 依赖 ``key`` 主键，故恰有一个竞争者胜出；并发（或重放）登记抛
        ``IntegrityError`` 并返回 False。与 ``idem_put``（``INSERT OR REPLACE``）不同，本方法**不**覆盖既有登记，故
        “绝不重复执行”即使跨进程也成立。参数：key；at。返回：新登记则 True，键已存在则 False。
        """
        try:
            self._conn.execute(
                "INSERT INTO idempotency (key, status, result, at) VALUES (?, 'pending', '', ?)", (key, at))
            self._conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def idem_complete(self, key: str, result: str, at: str = "") -> None:
        """Mark a claimed key ``done`` with its result (UPDATE; does not create).

        EN: Args: key; result; at (completion time). Returns: None. 中文：参数：key；result；at（完成时间）。返回：None。
        """
        self._conn.execute("UPDATE idempotency SET status='done', result=?, at=? WHERE key=?", (result, at, key))
        self._conn.commit()

    def close(self) -> None:
        """Close the SQLite connection (hygiene; matches the local-store pattern).

        EN: Returns: None. 中文：返回：None。
        """
        self._conn.close()


__all__ = ["OrchestrationStore"]
