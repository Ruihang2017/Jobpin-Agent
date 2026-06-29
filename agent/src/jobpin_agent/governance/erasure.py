"""Data-subject erasure / correction pipeline (§1.5) — APP 11.2 / APP 13.

EN —
Erase everything about one data subject from the LIVE store and leave a truthful trail. The pipeline
(Production Plan §1.5 walkthrough): locate ``tenant:org:candidate:<id>`` → delete the structured rows
and cascade-delete the derived vectors by ``memory_key`` prefix (via the injected ``deleter`` — the §1.4
provider's ``delete``, which already cascades both stores) → clear the prefetch recall caches (so a
cached recall can't still echo the subject) → write an ``erase`` / ``ok`` audit row → register the
subject's backups to age out at the retention period (NOT cascaded immediately — the honest boundary).

The honest boundary (Production Plan §1.5): erasure is immediate in the live store; backups age out
naturally as the retention period expires. We do NOT promise GDPR-style instant full wiping — that is a
physical limitation of local-first + file backups, and de-identification of residual artefacts is the
§1.11 pipeline. ``correct`` (APP 13) is a thin re-ingest-through-the-gate wrapper, left to the caller.

中文 —
把一个数据主体的全部内容从**实时**存储擦除并留下诚实痕迹。流水线（生产计划 §1.5 演练）：定位
``tenant:org:candidate:<id>`` → 删除结构化行并按 ``memory_key`` 前缀级联删除派生向量（经注入的 ``deleter``——§1.4
provider 的 ``delete``，其已级联两个存储）→ 清空 prefetch 召回缓存（使缓存的召回不再回显该主体）→ 写一条 ``erase`` /
``ok`` 审计 → 把该主体的备份登记为按留存期老化（不立即级联——诚实边界）。

诚实边界（生产计划 §1.5）：擦除在实时存储即刻生效；备份随留存期到期自然老化。我们不承诺 GDPR 式即时全清——这是
本地优先 + 文件备份的物理限制，残留物的去标识化属于 §1.11 流水线。``correct``（APP 13）为经门控重新 ingest 的薄封装，
交由调用方。
"""
from __future__ import annotations

from typing import Callable, Dict, List

from .audit import AuditLog
from .retention import BackupAgeingRegister


class Eraser:
    """Orchestrates a data-subject erasure over the §1.4 delete-cascade + cache + audit + register.

    EN —
    Construct with an ``AuditLog``, a ``BackupAgeingRegister``, and the recall-cache clearers (e.g.
    ``[composite.clear_recall_cache]``). ``erase`` runs the full pipeline against an injected ``deleter``.

    中文 —
    用 ``AuditLog``、``BackupAgeingRegister`` 与召回缓存清理器（如 ``[composite.clear_recall_cache]``）构造。``erase``
    针对注入的 ``deleter`` 运行完整流水线。
    """

    def __init__(self, audit: AuditLog, register: BackupAgeingRegister,
                 cache_clearers: List[Callable[[], None]]) -> None:
        """Wire the eraser to its audit log, backup register, and cache clearers.

        EN: Args: audit; register; cache_clearers (called after the delete). 中文：参数：audit；register；
            cache_clearers（删除后调用）。
        """
        self._audit = audit
        self._register = register
        self._clearers = list(cache_clearers)

    def erase(self, memory_key: str, *, actor: str, reason: str = "",
              deleter: Callable[[str], Dict[str, int]],
              now_days: float = 0.0, ages_out_at_days: float = 180.0) -> dict:
        """Run the erasure pipeline for one data subject.

        EN —
        Args: memory_key (the subject's key/prefix); actor (audit actor); reason (the compliance basis);
        deleter (deletes live rows+vectors and returns counts — the §1.4 provider's ``delete``);
        now_days / ages_out_at_days (the backup-ageing window). Returns: ``{"deleted": <counts>, "audit":
        "ok"}``. Cache-clear failures are swallowed (best-effort; the delete + audit are authoritative).

        中文 —
        参数：memory_key（主体键/前缀）；actor（审计执行者）；reason（合规依据）；deleter（删除实时行+向量并返回计数——
        §1.4 provider 的 ``delete``）；now_days / ages_out_at_days（备份老化窗口）。返回：``{"deleted": <计数>, "audit":
        "ok"}``。缓存清理失败被吞（尽力而为；删除 + 审计为权威）。
        """
        try:
            deleted = deleter(memory_key)
        except Exception as exc:
            # A failed/partial delete MUST still leave a forensic trace (no silent loss of the attempt).
            self._audit.record(actor, "erase", memory_key,
                               reason=f"{reason} | deleter failed: {exc}", result="rejected:error")
            raise
        clear_errors = []
        for clear in self._clearers:
            try:
                clear()
            except Exception as exc:
                clear_errors.append(str(exc))
        # If a cache failed to clear, the subject could still be recalled — record that in the trail
        # rather than reporting a clean "ok".
        result = "ok" if not clear_errors else "ok:cache_warn"
        note = f"{reason} | deleted={deleted}"
        if clear_errors:
            note += f" | cache_clear_errors={clear_errors}"
        self._audit.record(actor, "erase", memory_key, reason=note, result=result)
        self._register.register(memory_key, erased_at_days=now_days, ages_out_at_days=ages_out_at_days)
        return {"deleted": deleted, "audit": result, "cache_errors": clear_errors}
