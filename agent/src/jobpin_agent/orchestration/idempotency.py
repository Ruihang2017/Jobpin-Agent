"""External side-effect idempotency — register before execute (§1.7).

EN —
A long-running process must never double-act on the outside world: a retry (or a replay after a crash)
must not send an offer email or create a calendar entry twice (Plan §1.7, contract ③). ``run_once`` binds
each side effect to a deterministic key (e.g. ``email:req_812:cand_7f3a:offer``) and **registers the key
intent BEFORE executing**, then records completion; a replay finding the key present **skips** (dedup-wins).

Honest boundary (a deliberate trade-off): a present key always skips, so a crash between "register intent"
and "execute" leaves the effect un-sent (at-most-once) — this favours **never double-sending** (a duplicate
offer email is a compliance/UX harm) over guaranteed delivery. A "reconcile pending against the provider,
retry only if truly not sent" pass is a deferred enhancement, appropriate once real connectors land
(§1.10/M3).

中文 —
长程流程绝不能对外界重复作用：重试（或崩溃后重放）不得重复发出 offer 邮件或重复创建日历项（计划 §1.7 契约③）。
``run_once`` 把每个副作用绑定到确定性键（如 ``email:req_812:cand_7f3a:offer``），并在**执行前先登记键意图**，随后记录完成；
重放发现键已存在则**跳过**（去重优先）。

诚实边界（刻意权衡）：键已存在即跳过，故“登记意图”与“执行”之间崩溃会使副作用未发出（至多一次）——这偏向**绝不重复发送**
（重复 offer 邮件是合规/体验之害）而非保证送达。“与提供方对账 pending、仅在确实未发出时重试”的一遍是推迟的增强，待真实
连接器落地（§1.10/M3）适用。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Tuple

from .store import OrchestrationStore


class IdempotencyStore:
    """Register-before-execute dedup for external side effects, backed by the orchestration store (§1.7).

    EN: Construct over an ``OrchestrationStore`` (shares its SQLite file, so a restart sees the keys).
    中文：在 ``OrchestrationStore`` 上构造（共享其 SQLite 文件，故重启可见键）。
    """

    def __init__(self, store: OrchestrationStore) -> None:
        """Wrap an orchestration store.

        EN: Args: store. 中文：参数：store。
        """
        self._store = store

    def run_once(self, key: str, effect_fn: Callable[[], str]) -> Tuple[str, bool]:
        """Execute ``effect_fn`` at most once per ``key``; dedup a replay/retry.

        EN —
        Args: key (a deterministic idempotency key); effect_fn (the external side effect, returns a result
        string). Returns: ``(result, executed)`` — if ``key`` is already registered, returns its recorded
        result with ``executed=False`` (skip, never re-run); else registers the key as ``pending`` BEFORE
        calling ``effect_fn``, records ``done`` + the result, and returns ``(result, True)``. A crash after
        ``pending`` but before ``done`` leaves the key present → a replay skips (never re-sends).

        中文 —
        参数：key（确定性幂等键）；effect_fn（外部副作用，返回结果串）。返回：``(result, executed)``——若 ``key`` 已登记，
        返回其记录结果且 ``executed=False``（跳过，绝不重跑）；否则在调用 ``effect_fn`` **前**将键登记为 ``pending``，记录
        ``done`` + 结果，返回 ``(result, True)``。``pending`` 后、``done`` 前崩溃使键已存在 → 重放跳过（绝不重发）。
        """
        existing = self._store.idem_get(key)
        if existing is not None:
            return existing.get("result", ""), False
        # Atomically CLAIM the key as pending (plain INSERT; the PK makes exactly one racer win). A
        # concurrent/replayed claim loses here and skips — closing the check-then-act double-send race (M2).
        if not self._store.idem_begin(key, datetime.now(timezone.utc).isoformat()):
            existing = self._store.idem_get(key) or {}
            return existing.get("result", ""), False
        result = effect_fn()                                                       # the external side effect
        self._store.idem_complete(key, str(result), datetime.now(timezone.utc).isoformat())  # mark done (own ts)
        return str(result), True


__all__ = ["IdempotencyStore"]
