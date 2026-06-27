"""Deterministic system-prompt assembly (Key Invariant #1: identical input ->
byte-identical output). Order/design borrowed from Hermes system_prompt.py,
rewritten minimal. Memory/provider slots are filled by §1.2+."""
from __future__ import annotations

from dataclasses import dataclass, field

from .tools import ToolSpec


@dataclass
class SystemPromptParts:
    org_policy: str = ""
    compliance: str = ""
    role_permissions: str = ""
    memory_snapshot: str = ""   # filled by §1.2+
    provider_block: str = ""    # filled by §1.3+
    tools: list[ToolSpec] = field(default_factory=list)


def format_tools(tools: list[ToolSpec]) -> str:
    if not tools:
        return "(no tools available)"
    return "\n".join(f"- {t.name}: {t.description}" for t in sorted(tools, key=lambda s: s.name))


def build_system_prompt(parts: SystemPromptParts) -> str:
    sections = [
        "## Organisation policy", parts.org_policy or "(none)",
        "## Compliance constraints", parts.compliance or "(none)",
        "## Role permissions", parts.role_permissions or "(none)",
        "## Memory", parts.memory_snapshot or "(none)",
        "## Provider context", parts.provider_block or "(none)",
        "## Tools", format_tools(parts.tools),
    ]
    return "\n\n".join(sections) + "\n"
