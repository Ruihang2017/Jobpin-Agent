"""Governance write-gate — reject unlabelled / unconsented / biased writes (§1.5).

EN —
The first-class pre-check of the governed write path (Production Plan §1.5), inheriting Hermes's "reject
invalid writes outright" stance (Key Invariant 4). Given an intended write and its governance labels,
``validate`` either rejects it with an audit code (``rejected:no_provenance`` / ``rejected:no_consent`` /
``rejected:bias`` / ``flagged:bias``) or accepts it and returns the rendered governance header to prefix
onto the stored entry — so 100% of accepted writes carry provenance + a lawful-basis label. Rejections
are recorded to the audit log here; a committed write is audited by the caller (which knows the store
actually committed). ``remove`` carries no new content, so it skips provenance/consent/bias.

中文 —
受治理写路径的一等公民预检（生产计划 §1.5），继承 Hermes“直接拒绝无效写入”的立场（关键不变量 4）。给定一次拟写入及其
治理标签，``validate`` 要么以审计码拒绝（``rejected:no_provenance`` / ``rejected:no_consent`` / ``rejected:bias`` /
``flagged:bias``），要么接受并返回渲染好的治理头以前缀到存储条目——使 100% 被接受的写入携带来源 + 合法依据标签。拒绝
在此记入审计日志；已提交的写入由调用方审计（其知道存储确已提交）。``remove`` 不带新内容，故跳过来源/同意/偏见检查。
"""
from __future__ import annotations

from dataclasses import dataclass

from .audit import AuditLog
from .bias_hygiene import scan as default_bias_scan
from .labels import CONSENT_REQUIRED_SOURCE_TYPES, ConsentLabel, Provenance, render_header


@dataclass
class Decision:
    """The outcome of a write-gate check.

    EN: Attributes: ok (accepted?); code (the ``rejected:*`` / ``flagged:*`` code on rejection, else "");
        header (the rendered governance header to prefix on the entry, on acceptance).
    中文：属性：ok（是否接受）；code（拒绝时的 ``rejected:*`` / ``flagged:*`` 码，否则为 ""）；header（接受时要前缀到
        条目的渲染治理头）。
    """

    ok: bool
    code: str = ""
    header: str = ""


class GovernanceGate:
    """Validates an intended memory write against provenance / consent / bias-hygiene rules.

    EN —
    Construct with an ``AuditLog`` (exposed as ``.audit`` so the caller can record the committed write)
    and, optionally, a bias scanner (default ``bias_hygiene.scan``). ``validate`` is the pre-check.

    中文 —
    用 ``AuditLog`` 构造（暴露为 ``.audit`` 以便调用方记录已提交写入），并可选传入偏见扫描器（默认
    ``bias_hygiene.scan``）。``validate`` 即预检。
    """

    def __init__(self, audit: AuditLog, bias_scan=default_bias_scan) -> None:
        """Wire the gate to an audit log and a bias scanner.

        EN: Args: audit; bias_scan (default ``bias_hygiene.scan``). 中文：参数：audit；bias_scan（默认 ``bias_hygiene.scan``）。
        """
        self.audit = audit
        self._bias_scan = bias_scan

    def validate(self, action: str, target_key: str, body: str, prov: Provenance,
                 consent: ConsentLabel, retention_key: str, *, actor: str) -> Decision:
        """Pre-check a write: reject (and audit) on a violation, else accept with a rendered header.

        EN —
        Args: action (``add`` / ``replace`` / ``remove``); target_key (the memory_key); body (new
        content; ignored for ``remove``); prov; consent; retention_key; actor (the audit actor).
        Returns: a ``Decision`` — ``ok=False`` with a ``code`` (and an audit row recorded) on rejection;
        ``ok=True`` with ``header`` on acceptance (no audit row — the caller records the commit).

        中文 —
        参数：action（``add`` / ``replace`` / ``remove``）；target_key（memory_key）；body（新内容；``remove`` 忽略）；
        prov；consent；retention_key；actor（审计执行者）。返回：``Decision``——拒绝时 ``ok=False`` 带 ``code``（并记一条
        审计）；接受时 ``ok=True`` 带 ``header``（不记审计——由调用方记录提交）。
        """
        if action == "remove":
            return Decision(ok=True)
        if not prov.source_ref or not prov.source_type:
            self.audit.record(actor, f"write:{action}", target_key, result="rejected:no_provenance")
            return Decision(False, "rejected:no_provenance")
        if prov.source_type in CONSENT_REQUIRED_SOURCE_TYPES and not consent.consent_id:
            self.audit.record(actor, f"write:{action}", target_key, result="rejected:no_consent")
            return Decision(False, "rejected:no_consent")
        finding = self._bias_scan(body)
        if finding is not None:
            self.audit.record(actor, f"write:{action}", target_key, reason=finding.reason, result=finding.code)
            return Decision(False, finding.code)
        return Decision(True, header=render_header(prov, consent, retention_key))

    def validate_entity_ingest(self, memory_key: str, consent_status: str, source_refs, *, actor: str) -> Decision:
        """Pre-check an entity (candidate/employee) ingest: require provenance + granted consent.

        EN —
        The candidate/entity write path has no model tool, so its governance is enforced here at ingest
        (Production Plan §1.5 "100% of written memory carries provenance + a lawful-basis label"). Bias
        hygiene is deliberately NOT run on entity content — rejecting a résumé because it contains
        "female"/"age" would itself be discriminatory; bias hygiene targets recruiter-bar calibration
        (PRD §9.4/§9.5), not candidate data. The full consent-capture + de-identification pipeline is
        §1.11; §1.5 enforces the gate over the existing ingest seam.
        Args: memory_key; consent_status (e.g. "granted"/"withdrawn"/"unknown"); source_refs (the chunk
        provenance pointers — at least one non-empty required); actor. Returns: a ``Decision`` (rejection
        is audited as ``write:ingest`` / ``rejected:no_provenance`` | ``rejected:no_consent``).

        中文 —
        候选人/实体写路径没有模型工具，故其治理在此于 ingest 强制（生产计划 §1.5“100% 写入携带来源 + 合法依据标签”）。
        刻意**不**对实体内容运行偏见卫生——因简历含 "female"/"age" 而拒绝本身即构成歧视；偏见卫生针对招聘“标尺”校准
        （PRD §9.4/§9.5），而非候选人数据。完整的同意采集 + 去标识化流水线为 §1.11；§1.5 在既有 ingest 接缝上强制门控。
        参数：memory_key；consent_status（如 "granted"/"withdrawn"/"unknown"）；source_refs（片段来源指针——至少一个
        非空）；actor。返回：``Decision``（拒绝记为 ``write:ingest`` / ``rejected:no_provenance`` | ``rejected:no_consent``）。
        """
        refs = list(source_refs or [])
        if not refs or not all(refs):
            self.audit.record(actor, "write:ingest", memory_key, result="rejected:no_provenance")
            return Decision(False, "rejected:no_provenance")
        if consent_status != "granted":
            self.audit.record(actor, "write:ingest", memory_key,
                              reason=f"consent_status={consent_status}", result="rejected:no_consent")
            return Decision(False, "rejected:no_consent")
        return Decision(True)
