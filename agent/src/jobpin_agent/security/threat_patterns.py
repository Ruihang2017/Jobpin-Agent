"""Threat-pattern library for context-window security scanning — ported from Hermes (MIT).

EN —
Ported from Hermes ``tools/threat_patterns.py`` (MIT, Nous Research). The single source of truth for
prompt-injection / promptware / exfiltration patterns used by the context-assembly scanners (the §1.2
``MemoryStore`` ``scan_entry`` seam, the §1.4 candidate ingest seam, the §1.6 external-text door).

Pattern philosophy — patterns are organised by ATTACK CLASS, each a ``(regex, pattern_id, scope)`` tuple
where ``scope`` selects which scanners use it:
- ``"all"`` — everywhere (classic prompt injection, exfiltration);
- ``"context"`` — context files + memory + tool results (promptware / C2 / role hijack; broader);
- ``"strict"`` — memory writes + skill installs only (aggressive; acceptable for user-curated content).
Anchoring is on **C2-specific vocabulary or unambiguous attack behaviour, NOT bossy English** ("you must"
alone is too common in legitimate instruction-writing). The ``(?:\\w+\\s+)*`` multi-word-bypass guard
defeats filler-word insertion ("ignore all PRIOR instructions"). Memory writes use ``strict``.

What changed vs Hermes (TEXTBOOK_SPEC Tenet 1): **logic and patterns are copied verbatim** (this is the
expensive-to-get-right security core); only the docstrings were made bilingual and this port-origin note
added. Do NOT loosen the scope philosophy into a flood of false positives on normal HR text.

中文 —
移植自 Hermes ``tools/threat_patterns.py``（MIT，Nous Research）。提示注入 / promptware / 外泄模式的单一事实来源，
供上下文装配扫描器使用（§1.2 ``MemoryStore`` ``scan_entry`` 接缝、§1.4 候选人 ingest 接缝、§1.6 外部文本入口）。

模式哲学——按**攻击类别**组织，每条为 ``(regex, pattern_id, scope)`` 元组，``scope`` 决定哪些扫描器使用：
- ``"all"``——处处（经典提示注入、外泄）；
- ``"context"``——上下文文件 + 记忆 + 工具结果（promptware / C2 / 角色劫持；更广）；
- ``"strict"``——仅记忆写入 + 技能安装（激进；对用户策展内容可接受）。
锚定于**C2 专有词汇或明确攻击行为，而非命令式英语**（单独的“you must”在正当指令写作中太常见）。``(?:\\w+\\s+)*``
多词绕过守卫挫败填充词插入（“ignore all PRIOR instructions”）。记忆写入用 ``strict``。

相对 Hermes 的改动（TEXTBOOK_SPEC 第一原则）：**逻辑与模式逐字复制**（这是最昂贵、最易出错的安全核心）；仅将文档串
双语化并加此移植说明。切勿把范围哲学放松成对正常 HR 文本的误报洪流。
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

# Each entry: (regex, pattern_id, scope). scope ∈ {"all", "context", "strict"}. Copied verbatim from Hermes.
_PATTERNS: List[Tuple[str, str, str]] = [
    # ── Classic prompt injection (applies everywhere) ────────────────
    (r'ignore\s+(?:\w+\s+)*(previous|all|above|prior)\s+(?:\w+\s+)*instructions', "prompt_injection", "all"),
    (r'system\s+prompt\s+override', "sys_prompt_override", "all"),
    (r'disregard\s+(?:\w+\s+)*(your|all|any)\s+(?:\w+\s+)*(instructions|rules|guidelines)', "disregard_rules", "all"),
    (r'act\s+as\s+(if|though)\s+(?:\w+\s+)*you\s+(?:\w+\s+)*(have\s+no|don\'t\s+have)\s+(?:\w+\s+)*(restrictions|limits|rules)', "bypass_restrictions", "all"),
    (r'<!--[^>]*(?:ignore|override|system|secret|hidden)[^>]*-->', "html_comment_injection", "all"),
    (r'<\s*div\s+style\s*=\s*["\'][\s\S]*?display\s*:\s*none', "hidden_div", "all"),
    (r'translate\s+.*\s+into\s+.*\s+and\s+(execute|run|eval)', "translate_execute", "all"),
    (r'do\s+not\s+(?:\w+\s+)*tell\s+(?:\w+\s+)*the\s+user', "deception_hide", "all"),

    # ── Role-play / identity hijack (context scope) ──────────────────
    (r'you\s+are\s+(?:\w+\s+)*now\s+(?:a|an|the)\s+', "role_hijack", "context"),
    (r'pretend\s+(?:\w+\s+)*(you\s+are|to\s+be)\s+', "role_pretend", "context"),
    (r'output\s+(?:\w+\s+)*(system|initial)\s+prompt', "leak_system_prompt", "context"),
    (r'(respond|answer|reply)\s+without\s+(?:\w+\s+)*(restrictions|limitations|filters|safety)', "remove_filters", "context"),
    (r'you\s+have\s+been\s+(?:\w+\s+)*(updated|upgraded|patched)\s+to', "fake_update", "context"),
    (r'\bname\s+yourself\s+\w+', "identity_override", "context"),

    # ── C2 / Brainworm-style promptware (context scope) ──────────────
    (r'register\s+(as\s+)?a?\s*node', "c2_node_registration", "context"),
    (r'(heartbeat|beacon|check[\s\-]?in)\s+(to|with)\s+', "c2_heartbeat", "context"),
    (r'pull\s+(down\s+)?(?:new\s+)?task(?:ing|s)?\b', "c2_task_pull", "context"),
    (r'connect\s+to\s+the\s+network\b', "c2_network_connect", "context"),
    (r'you\s+must\s+(?:\w+\s+){0,3}(register|connect|report|beacon)\b', "forced_action", "context"),
    (r'only\s+use\s+one[\s\-]?liners?\b', "anti_forensic_oneliner", "context"),
    (r'never\s+(?:\w+\s+)*(?:create|write)\s+(?:\w+\s+)*(?:script|file)\s+(?:\w+\s+)*disk', "anti_forensic_disk", "context"),
    (r'unset\s+\w*(?:CLAUDE|CODEX|HERMES|AGENT|OPENAI|ANTHROPIC)\w*', "env_var_unset_agent", "context"),

    # ── Known C2 / red-team framework names (warn-only by default) ───
    (r'\b(?:cobalt\s*strike|sliver|havoc|mythic|metasploit|brainworm)\b', "known_c2_framework", "context"),
    (r'\bc2\s+(?:server|channel|infrastructure|beacon)\b', "c2_explicit", "context"),
    (r'\bcommand\s+and\s+control\b', "c2_explicit_long", "context"),

    # ── Exfiltration via curl/wget/cat with secrets ──────────────────
    (r'curl\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|API)', "exfil_curl", "all"),
    (r'wget\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|API)', "exfil_wget", "all"),
    (r'cat\s+[^\n]*(\.env|credentials|\.netrc|\.pgpass|\.npmrc|\.pypirc)', "read_secrets", "all"),
    (r'(send|post|upload|transmit)\s+.*\s+(to|at)\s+https?://', "send_to_url", "strict"),
    (r'(include|output|print|share)\s+(?:\w+\s+)*(conversation|chat\s+history|previous\s+messages|full\s+context|entire\s+context)', "context_exfil", "strict"),

    # ── Persistence / SSH backdoor (strict scope — memory + skills) ──
    (r'authorized_keys', "ssh_backdoor", "strict"),
    (r'\$HOME/\.ssh|\~/\.ssh', "ssh_access", "strict"),
    (r'\$HOME/\.hermes/\.env|\~/\.hermes/\.env', "hermes_env", "strict"),
    (r'(update|modify|edit|write|change|append|add\s+to)\s+.*(?:AGENTS\.md|CLAUDE\.md|\.cursorrules|\.clinerules)', "agent_config_mod", "strict"),
    (r'(update|modify|edit|write|change|append|add\s+to)\s+.*\.hermes/(config\.yaml|SOUL\.md)', "hermes_config_mod", "strict"),

    # ── Hardcoded secrets ────────────────────────────────────────────
    (r'(?:api[_-]?key|token|secret|password)\s*[=:]\s*["\'][A-Za-z0-9+/=_-]{20,}', "hardcoded_secret", "strict"),
]

# Invisible / bidirectional unicode characters used in injection attacks (verbatim from Hermes, given as
# explicit codepoints so no literal invisible char sits in source): zero-width joiners (200B-200D), word
# joiner (2060), invisible math operators (2062-2064), BOM (FEFF), bidi embeds/overrides (202A-202E),
# directional isolates (2066-2069).
_INVISIBLE_CODEPOINTS = (
    0x200B, 0x200C, 0x200D, 0x2060, 0x2062, 0x2063, 0x2064, 0xFEFF,
    0x202A, 0x202B, 0x202C, 0x202D, 0x202E, 0x2066, 0x2067, 0x2068, 0x2069,
)
INVISIBLE_CHARS = frozenset(chr(cp) for cp in _INVISIBLE_CODEPOINTS)

# Compiled pattern sets, indexed by scope. Compiled once at import time.
_COMPILED: dict[str, List[Tuple[re.Pattern, str]]] = {}


def _compile() -> None:
    """Compile pattern sets per scope (all subset of context subset of strict) (ported verbatim).

    EN: ``"all"`` lands in every set; ``"context"`` in context + strict; ``"strict"`` in strict only.
        Returns: None (populates the module ``_COMPILED`` cache). Raises: ValueError on an unknown scope.
    中文：``"all"`` 进入每个集合；``"context"`` 进入 context + strict；``"strict"`` 仅进入 strict。
        返回：None（填充模块 ``_COMPILED`` 缓存）。抛出：未知 scope 时 ValueError。
    """
    global _COMPILED
    if _COMPILED:
        return

    all_patterns: List[Tuple[re.Pattern, str]] = []
    context_patterns: List[Tuple[re.Pattern, str]] = []
    strict_patterns: List[Tuple[re.Pattern, str]] = []

    for pattern, pid, scope in _PATTERNS:
        compiled = re.compile(pattern, re.IGNORECASE)
        entry = (compiled, pid)
        if scope == "all":
            all_patterns.append(entry)
            context_patterns.append(entry)
            strict_patterns.append(entry)
        elif scope == "context":
            context_patterns.append(entry)
            strict_patterns.append(entry)
        elif scope == "strict":
            strict_patterns.append(entry)
        else:
            raise ValueError(f"threat_patterns: unknown scope {scope!r} for pattern {pid!r}")

    _COMPILED = {"all": all_patterns, "context": context_patterns, "strict": strict_patterns}


_compile()


def scan_for_threats(content: str, scope: str = "context") -> List[str]:
    """Return the matched pattern IDs in ``content`` at the given scope (ported verbatim).

    EN —
    Args: content; scope (``"all"`` narrow / ``"context"`` default / ``"strict"`` broad). Returns: a list
    of matched pattern IDs (+ ``invisible_unicode_U+XXXX`` findings); empty if clean. Raises: ValueError
    on an unknown scope.

    中文 —
    参数：content；scope（``"all"`` 窄 / ``"context"`` 默认 / ``"strict"`` 广）。返回：匹配的 pattern ID 列表
    （+ ``invisible_unicode_U+XXXX`` 命中）；干净则为空。抛出：未知 scope 时 ValueError。
    """
    if not content:
        return []

    findings: List[str] = []
    char_set = set(content)
    invisible_hits = char_set & INVISIBLE_CHARS
    for ch in invisible_hits:
        findings.append(f"invisible_unicode_U+{ord(ch):04X}")

    patterns = _COMPILED.get(scope)
    if patterns is None:
        raise ValueError(f"scan_for_threats: unknown scope {scope!r}")
    for compiled, pid in patterns:
        if compiled.search(content):
            findings.append(pid)

    return findings


def first_threat_message(content: str, scope: str = "strict") -> Optional[str]:
    """Return a human-readable block message for the first threat found, or None (ported verbatim).

    EN —
    The convenience wrapper used by blocking paths (memory writes, external ingest) — it matches the §1.2
    ``scan_entry`` seam shape ``Callable[[str], Optional[str]]``.
    Args: content; scope (default ``"strict"``). Returns: a block message, or None if clean.

    中文 —
    阻断路径（记忆写入、外部 ingest）使用的便捷封装——其形态匹配 §1.2 ``scan_entry`` 接缝
    ``Callable[[str], Optional[str]]``。参数：content；scope（默认 ``"strict"``）。返回：阻断消息，干净则 None。
    """
    findings = scan_for_threats(content, scope=scope)
    if not findings:
        return None
    pid = findings[0]
    if pid.startswith("invisible_unicode_"):
        codepoint = pid.replace("invisible_unicode_", "")
        return f"Blocked: content contains invisible unicode character {codepoint} (possible injection)."
    return (
        f"Blocked: content matches threat pattern '{pid}'. "
        f"Content is injected into the system prompt and must not contain "
        f"injection or exfiltration payloads."
    )


__all__ = ["INVISIBLE_CHARS", "scan_for_threats", "first_threat_message"]
