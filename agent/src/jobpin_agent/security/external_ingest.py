"""External-text ingest door — mandatory scan + fence (§1.6, hardening point ①).

EN —
Résumés, emails, and JDs are **untrusted input** and a real prompt-injection surface. This is the single
door all external text must pass before it can enter the model's context or memory: it runs the
``threat_patterns`` scan and, only if clean, wraps the text in the §1.3 ``<memory-context>`` fence (which
labels it "recalled reference data, NOT new user input"). On a threat hit the caller gets ``blocked=True``
+ the findings and the text is **never** wrapped/returned for downstream use. This is net-new wiring (not
a Hermes file port) that composes the ported scanner + the ported fence.

中文 —
简历、邮件与 JD 是**不可信输入**且为真实提示注入面。这是所有外部文本进入模型上下文或记忆前必须经过的唯一入口：运行
``threat_patterns`` 扫描，仅在干净时用 §1.3 ``<memory-context>`` 围栏包裹（标注其为“召回参考数据，而非新用户输入”）。
命中威胁时调用方得到 ``blocked=True`` + 命中项，且文本**绝不**被包裹/返回供下游使用。这是新增接线（非 Hermes 文件移植），
组合移植的扫描器 + 移植的围栏。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List

from ..memory.fence import build_memory_context_block
from .threat_patterns import scan_for_threats


@dataclass
class IngestResult:
    """The outcome of ingesting one piece of external text.

    EN: Attributes: ok (clean + fenced?); fenced (the ``<memory-context>`` block, or "" if blocked);
        findings (matched threat pattern IDs); blocked (a threat was found).
    中文：属性：ok（干净且已围栏？）；fenced（``<memory-context>`` 块，被阻断则 ""）；findings（命中的威胁模式 ID）；
        blocked（发现威胁）。
    """

    ok: bool
    fenced: str = ""
    findings: List[str] = field(default_factory=list)
    blocked: bool = False


def ingest_external_text(
    text: str,
    *,
    source: str,
    scope: str = "context",
    scan: Callable[[str, str], list] = scan_for_threats,
    fence: Callable[[str], str] = build_memory_context_block,
) -> IngestResult:
    """Scan external text and, if clean, return it wrapped in the ``<memory-context>`` fence.

    EN —
    Args: text (the untrusted external content); source (a label for the caller's audit/citation, e.g.
    ``"resume:cand_ada"``); scope (threat-scan scope, default ``"context"``); scan / fence (injected for
    tests). Returns: an ``IngestResult`` — ``blocked=True`` + findings on a threat hit (``fenced=""``),
    else ``ok=True`` with the fenced block.

    中文 —
    参数：text（不可信外部内容）；source（调用方审计/引用标签，如 ``"resume:cand_ada"``）；scope（威胁扫描范围，默认
    ``"context"``）；scan / fence（测试注入）。返回：``IngestResult``——命中威胁时 ``blocked=True`` + findings
    （``fenced=""``），否则 ``ok=True`` 带围栏块。
    """
    findings = scan(text, scope)
    if findings:
        return IngestResult(ok=False, blocked=True, findings=list(findings))
    return IngestResult(ok=True, fenced=fence(text))


__all__ = ["IngestResult", "ingest_external_text"]
