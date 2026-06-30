"""Crash-recovery loader for the Layer B state machine (§1.7).

EN —
After the process is killed and restarted, a fresh ``ProcessEngine`` is reconstructed over the same SQLite
file; ``recover`` reads the persisted non-terminal instances (RUNNING / SUSPENDED / AWAITING_HITL) so the
caller can re-attach handlers and resume each from its last persisted state — no state loss, no
restart-from-zero (Plan §1.7, contract ①). Terminal instances (DONE / FAILED) are intentionally skipped.

中文 —
进程被杀死并重启后，在同一 SQLite 文件上重建一个新的 ``ProcessEngine``；``recover`` 读取持久化的非终止实例
（RUNNING / SUSPENDED / AWAITING_HITL），使调用方可重新挂接处理器并从各自最后持久化状态恢复——无状态丢失、不从零重启
（计划 §1.7 契约①）。终止实例（DONE / FAILED）刻意跳过。
"""
from __future__ import annotations

from typing import List

from .state_machine import ProcessInstance
from .store import OrchestrationStore


def recover(store: OrchestrationStore) -> List[ProcessInstance]:
    """Return the non-terminal process instances to resume after a restart.

    EN: Args: store (over the same DB file the killed process used). Returns: the RUNNING / SUSPENDED /
        AWAITING_HITL instances, each at its persisted ``current_state``.
    中文：参数：store（在被杀进程所用的同一 DB 文件上）。返回：RUNNING / SUSPENDED / AWAITING_HITL 实例，各处其持久化
        ``current_state``。
    """
    return store.non_terminal_instances()


__all__ = ["recover"]
