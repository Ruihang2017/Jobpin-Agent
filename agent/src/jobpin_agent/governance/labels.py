"""Governance labels + the in-entry governance header (§1.5).

EN —
The metadata that wraps each memory entry (Production Plan §1.5): provenance (where it came from,
back-linking to evidence — APP 1), a lawful-basis / consent label (APP 3/5/6), and a retention policy
(APP 11.2). §1.2 pre-committed to carrying these as a machine-parseable header **inside** one entry
(header and body share the entry so ``ENTRY_DELIMITER`` splitting is unaffected); this module renders
and parses that header. An entry with no ``---`` separator parses as unlabelled (the write path rejects
such writes).

中文 —
包裹每条记忆的元数据（生产计划 §1.5）：来源（从何而来，回链证据——APP 1）、合法依据/同意标签（APP 3/5/6）、
留存策略（APP 11.2）。§1.2 已预先承诺把它们作为可机读的头**置于**单条记忆内（头与正文同属一条，使
``ENTRY_DELIMITER`` 切分不受影响）；本模块负责渲染与解析该头。无 ``---`` 分隔符的条目解析为未标注（写路径拒绝
此类写入）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Source types that require a per-subject consent_id (APP 3/5/6); others rely on legitimate_interest/contract.
CONSENT_REQUIRED_SOURCE_TYPES = frozenset({"candidate_submitted", "candidate_volunteered", "third_party"})
# The permitted lawful bases.
LEGAL_BASES = frozenset({"consent", "legitimate_interest", "contract"})
# The line that separates the header from the body inside one entry.
_HEADER_SEP = "---"
# Matches a whole governance header block (``key:`` line → its label lines → the ``---`` line) anywhere in
# a string, so the header can be stripped from any model-facing render (snapshot / recall) while it stays
# on disk for the governance layer. Used by ``strip_governance_headers``.
_HEADER_BLOCK_RE = re.compile(
    r"^key:.*\n"
    r"(?:(?:source_type|source_ref|collected_at|collected_by|legal_basis|consent_id|purpose|retention_ttl):.*\n)*"
    r"---\n",
    re.MULTILINE,
)


@dataclass
class Provenance:
    """Where a memory entry came from, back-linking to the original evidence (APP 1).

    EN —
    Attributes: memory_key (the namespace key this entry belongs to); source_type (e.g.
    ``recruiter_input`` / ``candidate_submitted`` / ``public_jd``); source_ref (a pointer back to the
    original chunk / document — required); collected_at (ISO-8601 UTC); collected_by (the actor).

    中文 —
    属性：memory_key（本条目所属命名空间键）；source_type（如 ``recruiter_input`` / ``candidate_submitted`` /
    ``public_jd``）；source_ref（回指原片段/文档的指针——必需）；collected_at（ISO-8601 UTC）；collected_by（执行者）。
    """

    memory_key: str
    source_type: str
    source_ref: str = ""
    collected_at: str = ""
    collected_by: str = ""


@dataclass
class ConsentLabel:
    """The lawful-basis / consent label for a memory entry (APP 3/5/6).

    EN —
    Attributes: legal_basis (one of ``LEGAL_BASES``); purpose (collection purpose, e.g.
    ``hiring_calibration``); consent_id (pointer to the consent record — required when ``source_type``
    needs consent); use_scope (the permitted uses; out-of-scope recall is blocked by RBAC).

    中文 —
    属性：legal_basis（``LEGAL_BASES`` 之一）；purpose（采集目的，如 ``hiring_calibration``）；consent_id（指向同意
    记录——当 ``source_type`` 需要同意时必需）；use_scope（许可用途；超范围召回由 RBAC 阻断）。
    """

    legal_basis: str
    purpose: str = ""
    consent_id: str = ""
    use_scope: str = ""


@dataclass
class RetentionPolicy:
    """A retention / TTL policy (APP 11.2) — differentiated by hired / not-hired / withdrawn.

    EN: Attributes: policy_key (e.g. ``hired_5y``); ttl_days (lifetime in days); basis (legal/policy basis).
    中文：属性：policy_key（如 ``hired_5y``）；ttl_days（以天计的寿命）；basis（法律/政策依据）。
    """

    policy_key: str
    ttl_days: int
    basis: str = ""


def render_header(prov: Provenance, consent: ConsentLabel, retention_key: str) -> str:
    """Render the governance header for an entry (header + ``---`` separator).

    EN —
    Args: prov; consent; retention_key (a ``RetentionPolicy.policy_key``). Returns: the header text
    ending with ``---`` on its own line and a trailing newline, so the body can be concatenated directly.

    中文 —
    参数：prov；consent；retention_key（``RetentionPolicy.policy_key``）。返回：以独立成行的 ``---`` 与一个尾随换行
    结尾的头文本，使正文可直接拼接其后。
    """
    lines = [
        f"key: {prov.memory_key}",
        f"source_type: {prov.source_type}",
        f"source_ref: {prov.source_ref}",
        f"collected_at: {prov.collected_at}",
        f"collected_by: {prov.collected_by}",
        f"legal_basis: {consent.legal_basis}",
        f"consent_id: {consent.consent_id}",
        f"purpose: {consent.purpose}",
        f"retention_ttl: {retention_key}",
        _HEADER_SEP,
        "",
    ]
    return "\n".join(lines)


def parse_header(entry: str):
    """Split an entry into its governance header fields and its body.

    EN —
    Args: entry (header + ``---`` + body, or a plain unlabelled entry). Returns: ``(labels, body)`` —
    ``labels`` is a ``dict`` of header fields, or ``None`` if there is no ``---`` separator (unlabelled).

    中文 —
    参数：entry（头 + ``---`` + 正文，或无标注的纯条目）。返回：``(labels, body)``——``labels`` 为头字段的 ``dict``，
    若无 ``---`` 分隔符（未标注）则为 ``None``。
    """
    sep = f"\n{_HEADER_SEP}\n"
    if sep not in entry:
        return None, entry
    head, _sep, body = entry.partition(sep)
    labels = {}
    for line in head.splitlines():
        if ":" in line:
            key, _colon, value = line.partition(":")
            labels[key.strip()] = value.strip()
    return labels, body


def strip_governance_headers(text: str) -> str:
    """Remove every governance header block from a model-facing render (keep the bodies).

    EN —
    The in-entry governance header is metadata for the governance layer (Plan §1.2), NOT model content,
    and would otherwise bleed into the frozen system-prompt snapshot (and the curated char budget). This
    strips each header block (``key:`` line through its ``---``) wherever it appears, leaving any render
    chrome and the entry bodies intact. The header stays on disk for validation / back-linking.
    Args: text (a rendered snapshot/recall block, possibly containing several headered entries).
    Returns: the text with governance headers removed.

    中文 —
    条目内治理头是治理层的元数据（计划 §1.2），并非模型内容，否则会渗入冻结的系统提示快照（及策展字符预算）。本函数
    剥除每个头块（``key:`` 行至其 ``---``），无论其出现在何处，保留任何渲染外框与条目正文。头仍留在磁盘上供校验/回链。
    参数：text（渲染后的快照/召回块，可能含多条带头条目）。返回：移除治理头后的文本。
    """
    return _HEADER_BLOCK_RE.sub("", text)
