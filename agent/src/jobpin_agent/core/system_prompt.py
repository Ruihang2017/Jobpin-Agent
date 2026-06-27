"""Deterministic system-prompt assembly — the canonical bilingual-docstring example.

EN —
Builds the agent's system prompt from a fixed set of sections in a fixed order.
Determinism matters: identical input must yield byte-identical output, because a
stable system-prompt prefix is the prerequisite for prompt-cache hits and stable
behaviour (Key Invariant #1 in Production Plan §1.0). The ``memory_snapshot`` and
``provider_block`` slots are placeholders here; the Memory Subsystem (§1.2+) fills
them via ``MemoryStore.format_for_system_prompt()`` and ``MemoryProvider``. Design
borrowed from Hermes ``system_prompt.build_system_prompt`` /
``format_tools_for_system_message`` and rewritten minimal (PRD §2.7).

中文 —
按固定章节集合与固定顺序构建 agent 的系统提示。确定性很关键：相同输入必须产生逐字节一致的输出，因为
稳定的系统提示前缀是 prompt 缓存命中与行为稳定的前提（生产计划 §1.0 的关键不变量 #1）。此处
``memory_snapshot`` 与 ``provider_block`` 槽位为占位；记忆子系统（§1.2+）将经
``MemoryStore.format_for_system_prompt()`` 与 ``MemoryProvider`` 填充。设计借鉴自 Hermes 的
``system_prompt.build_system_prompt`` / ``format_tools_for_system_message`` 并重写为精简版（PRD §2.7）。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .tools import ToolSpec


@dataclass
class SystemPromptParts:
    """The sections that compose a system prompt.

    EN —
    Attributes:
        org_policy: Organisation policy text.
        compliance: Compliance constraints (e.g. Australian guardrails).
        role_permissions: The acting role and what it may do.
        memory_snapshot: Frozen memory snapshot slot — empty until §1.2 fills it
            once per session (it must NOT change mid-session — Key Invariant #1).
        provider_block: A memory provider's static system block — empty until §1.3.
        tools: Tools to advertise; rendered in name-sorted order for determinism.

    中文 —
    属性：
        org_policy：组织政策文本。
        compliance：合规约束（如澳洲护栏）。
        role_permissions：执行角色及其权限。
        memory_snapshot：冻结记忆快照槽位——在 §1.2 每会话填充一次前为空（会话中途不得改变——
            关键不变量 #1）。
        provider_block：记忆 provider 的静态系统块——在 §1.3 前为空。
        tools：要告知的工具；为确定性按名称排序渲染。
    """

    org_policy: str = ""
    compliance: str = ""
    role_permissions: str = ""
    memory_snapshot: str = ""   # filled by §1.2+
    provider_block: str = ""    # filled by §1.3+
    tools: list[ToolSpec] = field(default_factory=list)


def format_tools(tools: list[ToolSpec]) -> str:
    """Render a tool list as deterministic prompt text.

    EN —
    Tools are sorted by name so the output never depends on registration order
    (preserving byte-identical assembly).
    Args:
        tools: The tools to render.
    Returns:
        One ``- name: description`` line per tool, or a placeholder if empty.

    中文 —
    工具按名称排序，使输出不依赖注册顺序（保持逐字节一致装配）。
    参数：
        tools：要渲染的工具。
    返回：
        每个工具一行 ``- 名称: 描述``；若为空则返回占位文本。
    """
    if not tools:
        return "(no tools available)"
    return "\n".join(f"- {t.name}: {t.description}" for t in sorted(tools, key=lambda s: s.name))


def build_system_prompt(parts: SystemPromptParts) -> str:
    """Assemble the full system prompt deterministically.

    EN —
    Concatenates the sections in a FIXED order with stable headings, so identical
    ``parts`` always yield byte-identical text. This purity is what later enables
    a frozen snapshot + prompt caching (Key Invariant #1). Per-turn memory recall
    is deliberately NOT placed here — it belongs in the messages as a
    ``<memory-context>`` fence (see ``agent_loop``), keeping this prefix stable.
    Args:
        parts: The sections to assemble.
    Returns:
        The assembled prompt text, terminated by a single trailing newline.

    中文 —
    以固定顺序与稳定标题拼接各章节，使相同的 ``parts`` 始终产生逐字节一致的文本。此纯函数性正是后续
    冻结快照 + prompt 缓存得以成立的基础（关键不变量 #1）。每回合的记忆召回刻意不放在此处——它应作为
    ``<memory-context>`` 围栏放入消息中（见 ``agent_loop``），以保持该前缀稳定。
    参数：
        parts：要装配的各章节。
    返回：
        装配后的提示文本，以单个换行结尾。
    """
    sections = [
        "## Organisation policy", parts.org_policy or "(none)",
        "## Compliance constraints", parts.compliance or "(none)",
        "## Role permissions", parts.role_permissions or "(none)",
        "## Memory", parts.memory_snapshot or "(none)",
        "## Provider context", parts.provider_block or "(none)",
        "## Tools", format_tools(parts.tools),
    ]
    return "\n\n".join(sections) + "\n"
