"""Retention policies + TTL sweep + backup-ageing register (§1.5).

EN —
Candidate data expires per policy, differentiated for hired / not-hired / withdrawn (APP 11.2). This
module holds the policy registry, an explicit ``sweep`` that returns the keys whose TTL has elapsed
(a scheduler calls it — there is no background timer, keeping the module pure and testable), and the
``BackupAgeingRegister`` that records the honest erasure boundary: when a data subject is erased from
the live store, their backups are NOT cascaded immediately but age out as the retention period expires;
the register makes that pending ageing visible (Production Plan §1.5 "the honest boundary of erasure").

Days are used as the time unit so the functions are pure (no clock dependency) — callers pass the
current day and the policy's TTL is in days.

中文 —
候选人数据按策略过期，区分录用/未录用/撤回（APP 11.2）。本模块持有策略注册表、一个返回 TTL 已到期键的显式 ``sweep``
（由调度器调用——无后台定时器，使模块纯净可测），以及记录诚实擦除边界的 ``BackupAgeingRegister``：当数据主体从实时
存储被擦除，其备份不立即级联删除，而是随留存期到期自然老化；注册表使这一待老化可见（生产计划 §1.5“擦除的诚实边界”）。

以天为时间单位，使函数保持纯净（不依赖时钟）——调用方传入当前天数，策略 TTL 以天计。
"""
from __future__ import annotations

from typing import List, Tuple

from .labels import RetentionPolicy

# The differentiated retention policies (APP 11.2). Keyed by policy_key.
RETENTION_POLICIES = {
    "hired_5y": RetentionPolicy("hired_5y", 365 * 5, "employment record retention"),
    "not_hired_180d": RetentionPolicy("not_hired_180d", 180, "unsuccessful applicant retention"),
    "withdrawn_30d": RetentionPolicy("withdrawn_30d", 30, "withdrawn applicant data minimisation"),
}


def sweep(now_days: float, items: List[Tuple[str, float, str]]) -> List[str]:
    """Return the memory_keys whose retention TTL has elapsed.

    EN —
    Args: now_days (the current day); items (a list of ``(memory_key, collected_at_days, policy_key)``).
    Returns: the keys for which ``now_days - collected_at_days > policy.ttl_days`` (unknown policies are
    skipped — never auto-expired).

    中文 —
    参数：now_days（当前天数）；items（``(memory_key, collected_at_days, policy_key)`` 列表）。返回：满足
    ``now_days - collected_at_days > policy.ttl_days`` 的键（未知策略跳过——绝不自动过期）。
    """
    expired: List[str] = []
    for memory_key, collected_at_days, policy_key in items:
        policy = RETENTION_POLICIES.get(policy_key)
        if policy is not None and (now_days - collected_at_days) > policy.ttl_days:
            expired.append(memory_key)
    return expired


class BackupAgeingRegister:
    """Records erased subjects whose backups age out (not cascaded immediately) — the honest boundary.

    EN —
    When a subject is erased from the live store, ``register`` records ``(memory_key, erased_at,
    ages_out_at)``; ``pending`` lists the keys whose backups have not yet aged out as of a given day.
    This is the truthful "erasure = live now + backups age out" record (no GDPR-instant-wipe promise).

    中文 —
    当主体从实时存储被擦除，``register`` 记录 ``(memory_key, erased_at, ages_out_at)``；``pending`` 列出截至给定天数
    备份尚未老化的键。这是诚实的“擦除 = 实时即刻 + 备份老化”记录（不承诺 GDPR 式即时清除）。
    """

    def __init__(self) -> None:
        """Create an empty register.

        EN: Returns: None. 中文：返回：None。
        """
        self._entries: List[Tuple[str, float, float]] = []

    def register(self, memory_key: str, erased_at_days: float, ages_out_at_days: float) -> None:
        """Record that an erased subject's backups will age out at a future day.

        EN: Args: memory_key; erased_at_days; ages_out_at_days. Returns: None.
        中文：参数：memory_key；erased_at_days；ages_out_at_days。返回：None。
        """
        self._entries.append((memory_key, erased_at_days, ages_out_at_days))

    def pending(self, now_days: float) -> List[str]:
        """List keys whose backups have not yet aged out as of ``now_days``.

        EN: Args: now_days. Returns: the still-pending memory_keys.
        中文：参数：now_days。返回：仍待老化的 memory_key。
        """
        return [mk for mk, _erased, ages_out in self._entries if now_days < ages_out]
