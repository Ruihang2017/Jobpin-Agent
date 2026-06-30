"""The "fully local" switch + per-egress audit (§1.10) — the single outbound chokepoint.

EN —
Local-first means nothing leaves the machine unless an operator explicitly allows it. ``OutboundGuard`` is
the ONE place an outbound call may happen: ``send`` runs the wrapped ``call`` ONLY when the switch is off,
and records a §1.8 audit row for every attempt. ``fully_local`` defaults to **True** (the safe posture), so
by default the integration layer makes zero outbound calls — the wrapped ``call`` is never invoked and an
``OutboundBlocked`` is raised. The egress field set + de-identification status are encoded into the audit
``reason`` (the §1.8 ``audit_log`` has no dedicated columns — no migration this cycle); ``deid_status`` is a
seam §1.11's ``deid`` will set to the real masking status before any real-PII egress.

中文 —
本地优先意味着除非运维显式允许，否则没有任何东西离开本机。``OutboundGuard`` 是出站调用可能发生的**唯一**之处：``send``
仅在开关关闭时运行被包裹的 ``call``，并为每次尝试记录一行 §1.8 审计。``fully_local`` 默认 **True**（安全姿态），故默认
情况下集成层零出站——被包裹的 ``call`` 绝不被调用且抛出 ``OutboundBlocked``。出站字段集 + 脱敏状态被编码进审计 ``reason``
（§1.8 ``audit_log`` 无专用列——本周期不迁移）；``deid_status`` 是接缝，§1.11 的 ``deid`` 会在任何真实 PII 出站前将其设为
真实的脱敏状态。
"""
from __future__ import annotations

from typing import Callable, List, Optional, TypeVar

from ..data.audit import AuditStore

T = TypeVar("T")


class OutboundBlocked(Exception):
    """Raised when an outbound call is attempted while the fully-local switch is on.

    EN: Signals the local-first guarantee held — the wrapped call did NOT run. 中文：表示本地优先保证生效——被包裹的调用未运行。
    """


class OutboundGuard:
    """The single chokepoint every outbound call routes through (the "fully local" switch + egress audit).

    EN —
    Args (constructor): fully_local (default True — when True, 0 outbound); audit (optional §1.8
        ``AuditStore`` for the egress trail); actor (the audit actor).
    中文 —
    参数（构造器）：fully_local（默认 True——为 True 时 0 出站）；audit（可选的 §1.8 ``AuditStore`` 用于出站轨迹）；
        actor（审计 actor）。
    """

    def __init__(self, *, fully_local: bool = True, audit: Optional[AuditStore] = None,
                 actor: str = "system") -> None:
        """Args: fully_local; audit; actor. 中文 — 参数：fully_local；audit；actor。"""
        self.fully_local = fully_local
        self._audit = audit
        self._actor = actor

    def send(self, *, target: str, fields: List[str], reason: str, deid_status: str = "none",
             call: Callable[[], T]) -> T:
        """Run ``call`` iff the switch is off; record an egress audit row either way.

        EN —
        Args: target (the external system); fields (the field set leaving — encoded into the audit reason);
            reason (purpose, e.g. ``pull:candidate``); deid_status (§1.11 seam; ``none`` until de-id ships);
            call (the actual outbound operation, invoked ONLY when ``fully_local`` is False).
        Returns: ``call()``'s result (switch off). Raises: ``OutboundBlocked`` (switch on) — ``call`` is not
            invoked, guaranteeing 0 outbound.

        中文 —
        参数：target（外部系统）；fields（离开的字段集——编码进审计 reason）；reason（目的，如 ``pull:candidate``）；
            deid_status（§1.11 接缝；脱敏上线前为 ``none``）；call（实际出站操作，仅当 ``fully_local`` 为 False 时调用）。
        返回：``call()`` 的结果（开关关闭）。抛出：``OutboundBlocked``（开关打开）——``call`` 不被调用，保证 0 出站。
        审计：完全本地时在抛错**前**记一行 ``rejected:fully_local``；开关关闭时在调用**之后**按真实结果记 ``ok`` 或
        ``error``（失败则再抛出），使该出站轨迹如实反映结果。
        """
        detail = f"{reason} fields=[{','.join(fields)}] deid={deid_status}"
        if self.fully_local:
            if self._audit is not None:
                self._audit.record(self._actor, "egress", target, reason=detail, result="rejected:fully_local")
            raise OutboundBlocked(f"fully-local mode: outbound to {target} blocked")
        # Switch off: run the call and record the egress with its TRUE outcome (so a failed networked
        # call is never logged as "ok" — this audit is the APP-8 cross-border-disclosure trail).
        try:
            result = call()
        except Exception:
            if self._audit is not None:
                self._audit.record(self._actor, "egress", target, reason=detail, result="error")
            raise
        if self._audit is not None:
            self._audit.record(self._actor, "egress", target, reason=detail, result="ok")
        return result
