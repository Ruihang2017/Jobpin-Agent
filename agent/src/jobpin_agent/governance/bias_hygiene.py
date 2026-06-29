"""Bias-hygiene scanner — protected attributes + proxy variables (§1.5).

EN —
Australian anti-discrimination law (the four federal acts + AHRC) forbids using protected attributes
as decision features and is wary of indirect discrimination via proxy variables. This scanner runs on
write-calibrated content (org / recruiter "bar") before it enters memory: a protected attribute is
**rejected** (``rejected:bias``); a proxy-as-hard-threshold is **flagged** (``flagged:bias``) and the
write path blocks it. It feeds the Phase-1 bias audit.

HONEST BOUNDARY: this is a curated, deterministic heuristic starter set — keyword + regex — NOT a
complete classifier. It will miss novel phrasings and can false-positive. It exists to catch the
obvious cases and leave an audit trail; the Phase-1 bias audit owns the real model. Treat a clean scan
as "no obvious red flag", not "proven unbiased".

中文 —
澳大利亚反歧视法（四部联邦法 + AHRC）禁止以受保护属性作为决策特征，并警惕经代理变量的间接歧视。本扫描器在写校准
内容（组织/招聘“标准”）进入记忆前运行：受保护属性**拒绝**（``rejected:bias``）；作为硬阈值的代理变量**标记**
（``flagged:bias``）且写路径将其阻断。它馈入第一阶段偏见审计。

诚实边界：这是一套策展的、确定性的启发式起步集——关键词 + 正则——并非完整分类器。它会漏掉新表述，也可能误报。
其作用是抓住明显情形并留下审计痕迹；真正的模型由第一阶段偏见审计负责。干净的扫描应理解为“无明显红旗”，而非
“已证明无偏”。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class BiasFinding:
    """A bias-hygiene hit.

    EN: Attributes: code (``"rejected:bias"`` for a protected attribute, ``"flagged:bias"`` for a proxy);
        term (the matched term/pattern); reason (a human-readable explanation).
    中文：属性：code（受保护属性为 ``"rejected:bias"``，代理变量为 ``"flagged:bias"``）；term（命中的词/模式）；
        reason（可读解释）。
    """

    code: str
    term: str
    reason: str


# Protected attributes (Australian anti-discrimination grounds) as (label, word-boundary regex).
# CRITICAL: match on word boundaries, NOT raw substring — naive ``"age" in text`` false-positives on
# "manAGEment" / "manAGEr" / "lAGuage" / "coverAGE", and "race" on "gRACE" / "embRACE", which would make
# the gate hard-reject ordinary recruiter/HR vocabulary. Stems use ``\w*`` (e.g. pregnan/ethnic/disabilit).
PROTECTED_ATTRIBUTES: Tuple[Tuple[str, str], ...] = (
    ("age", r"\bage\b|\byears old\b|\bdate of birth\b"),
    ("gender", r"\bgender\b|\b(?:fe)?male\b"),
    ("race/ethnicity", r"\brace\b|\bethnic\w*\b|\bnationality\b"),
    ("marital/family status", r"\bmarried\b|\bmarital\b|\bfamily status\b|\bchildren\b|\bpregnan\w*\b"),
    ("religion", r"\breligio\w+\b"),
    ("disability/health", r"\bdisabilit\w+\b|\bhealth condition\b"),
    ("sexual orientation", r"\bsexual orientation\b"),
)
_PROTECTED_COMPILED = tuple((label, re.compile(pattern)) for label, pattern in PROTECTED_ATTRIBUTES)

# Proxy variables / indirect-discrimination patterns — flagged (blocked when used as a hard threshold).
PROXY_PATTERNS: Tuple[Tuple[str, str], ...] = (
    (r"\bgraduat(e|ed|ion)\b.{0,40}\b(group of eight|go8|ivy league|sandstone|elite)\b",
     "elite-school requirement is a socio-economic proxy"),
    (r"\b(must|required to)\b.{0,30}\b(postcode|suburb)\b", "postcode is a proxy for race/SES"),
    (r"\bgraduation year\b", "graduation year is an age proxy"),
    (r"\bnative (english )?speaker\b", "native-speaker requirement is a national-origin proxy"),
)


def scan(text: str) -> Optional[BiasFinding]:
    """Scan text for a protected attribute (reject) or a proxy variable (flag).

    EN —
    Args: text (the content about to be written to memory). Returns: a ``BiasFinding`` on the first hit
    (protected attribute checked first → ``rejected:bias``; then proxy → ``flagged:bias``), or ``None``
    if no obvious red flag. Matching is word-boundary based, so benign words that merely embed a token
    (e.g. "management", "language", "grace") do not trigger a false positive.

    中文 —
    参数：text（即将写入记忆的内容）。返回：首个命中时的 ``BiasFinding``（先查受保护属性 → ``rejected:bias``；再查
    代理变量 → ``flagged:bias``），无明显红旗则 ``None``。匹配基于词边界，故仅嵌入某 token 的良性词
    （如 "management"、"language"、"grace"）不会误报。
    """
    low = text.lower()
    for label, pattern in _PROTECTED_COMPILED:
        if pattern.search(low):
            return BiasFinding("rejected:bias", label, f"protected attribute referenced: {label}")
    for pattern, reason in PROXY_PATTERNS:
        if re.search(pattern, low):
            return BiasFinding("flagged:bias", pattern, reason)
    return None
