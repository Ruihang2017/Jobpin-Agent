"""Context compression with pre-compression fact-injection (§1.6) — fixing the Hermes gap.

EN —
Over a long hiring loop the message history grows past the context budget and must be compressed. Hermes
calls ``on_pre_compress(messages)`` at this point but **discards the return value** (a bare statement,
not an assignment — ``conversation_compression.py:459``), so key candidate facts/decisions can be lost.
This module wires it correctly (Plan §1.6, hardening point ②):

  1. when ``should_compress`` fires, split the history into [old | recent(keep_recent)];
  2. **capture** ``facts = hooks.on_pre_compress(old)`` (the Manager already aggregates providers' facts);
  3. **merge** ``facts`` into a summary message that replaces ``old`` via ``SessionStore.compact`` — so the
     fact rides in the ongoing context (recallable: it is sent to the model every subsequent turn);
  4. **best-effort persist** the facts through an injected ``persist_fn`` (the composition root routes it
     through the §1.5 ``GovernanceGate``) — belt-and-braces durability across sessions; a gate rejection
     (e.g. ``rejected:no_consent`` for an unlabelled extract) must NOT crash the turn.

Design borrowed from Hermes ``agent/conversation_compression.py`` and rewritten lean (PRD §2.7). The
summariser is an injected seam: the default is **deterministic and fact-preserving** (so the integration
test is offline + assertable); a real LLM summariser is wired via ``summarize_fn`` at config/§1.11.

中文 —
长招聘 loop 中消息历史会超出上下文预算而须压缩。Hermes 在此调用 ``on_pre_compress(messages)`` 却**丢弃返回值**
（裸语句而非赋值——``conversation_compression.py:459``），故关键候选人事实/决策可能丢失。本模块正确接线（计划 §1.6
强化点②）：(1) ``should_compress`` 触发时把历史切为 [old | 最近 keep_recent]；(2) **捕获** ``facts =
hooks.on_pre_compress(old)``（Manager 已聚合各 provider 事实）；(3) 把 ``facts`` **并入**替换 ``old`` 的摘要消息
（经 ``SessionStore.compact``）——使事实留在后续上下文中（可召回：每个后续回合都发给模型）；(4) 经注入的 ``persist_fn``
**尽力持久化**事实（组合根经 §1.5 ``GovernanceGate`` 路由）——跨会话的双保险；门控拒绝（如未标注抽取的
``rejected:no_consent``）**不得**使回合崩溃。

设计借鉴 Hermes ``agent/conversation_compression.py`` 并重写为精简版（PRD §2.7）。摘要器为注入接缝：默认**确定性且
保真**（使集成测试离线且可断言）；真实 LLM 摘要器经 ``summarize_fn`` 在配置/§1.11 接入。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, List, Optional

from .messages import Message, Role

if TYPE_CHECKING:  # hints only (avoids a core→core import at runtime)
    from .hooks import MemoryHooks
    from .session_store import SessionStore

# HONEST SCOPE NOTE (§1.6): the default summariser is fact-PRESERVING, not token-REDUCING — it digests
# the folded turns verbatim and appends the captured facts, so it bounds the message COUNT (so the loop
# does not re-fire) but NOT the token footprint, which can still grow across repeated compressions. The
# real lossy/abstractive summariser that controls the context budget is the ``summarize_fn`` seam, wired
# at §1.11/config with the model. Until then, do not rely on this as a token-budget control.


def default_summarize(old_messages: List[Message], facts: str) -> str:
    """Build a deterministic, fact-preserving summary of the folded messages.

    EN —
    Args: old_messages (the messages about to be replaced); facts (the captured ``on_pre_compress``
    output). Returns: a summary string = a header + the retained ``facts`` (if any) + a digest of each
    folded turn's content. Deterministic so "the summary contains the fact" is assertable; a real LLM
    summariser replaces this via the ``summarize_fn`` seam.

    中文 —
    参数：old_messages（即将被替换的消息）；facts（捕获的 ``on_pre_compress`` 输出）。返回：摘要串 = 头部 + 保留的
    ``facts``（若有）+ 每条被折叠回合内容的摘要。确定性，使“摘要含该事实”可断言；真实 LLM 摘要器经 ``summarize_fn``
    接缝替换之。
    """
    lines = ["[compressed-summary] earlier conversation folded to save context."]
    if facts and facts.strip():
        lines.append("Key facts retained:\n" + facts.strip())
    digest = [f"- {m.role.value}: {m.content.strip()}" for m in old_messages if m.content and m.content.strip()]
    if digest:
        lines.append("Digest of folded turns:\n" + "\n".join(digest))
    return "\n\n".join(lines)


@dataclass
class CompressionResult:
    """The outcome of a ``compress`` call.

    EN: Attributes: compressed (did it fold?); summary (the summary text written, or ""); facts (the
        captured pre-compression facts); persisted (did the gated ``persist_fn`` succeed?).
    中文：属性：compressed（是否折叠）；summary（写入的摘要文本，或 ""）；facts（捕获的压缩前事实）；persisted
        （门控 ``persist_fn`` 是否成功）。
    """

    compressed: bool
    summary: str = ""
    facts: str = ""
    persisted: bool = False


class ContextCompressor:
    """Triggers context compression and wires pre-compression fact-injection (§1.6).

    EN —
    Construct with thresholds + seams; the agent loop calls ``should_compress`` then ``compress`` at the
    top of a turn (opt-in: the loop runs without one if ``compressor=None``). ``compress`` captures the
    ``on_pre_compress`` facts, folds the old messages into a summary that retains them, and best-effort
    persists them through ``persist_fn``.

    中文 —
    用阈值 + 接缝构造；agent 循环在回合开头调用 ``should_compress`` 再 ``compress``（可选：``compressor=None`` 时循环
    无压缩运行）。``compress`` 捕获 ``on_pre_compress`` 事实，把旧消息折叠为保留它们的摘要，并经 ``persist_fn`` 尽力持久化。
    """

    def __init__(
        self,
        *,
        max_messages: int = 20,
        keep_recent: int = 6,
        summarize_fn: Callable[[List[Message], str], str] = default_summarize,
        persist_fn: Optional[Callable[[str], bool]] = None,
    ) -> None:
        """Configure the compressor.

        EN: Args: max_messages (compress when history exceeds this); keep_recent (recent turns kept
            verbatim — keep ``>= 1`` so the current turn's user message survives as a standalone message,
            not only inside the summary digest; the agent loop compresses after appending the user turn);
            summarize_fn (default deterministic, fact-preserving — see the module-level scope note);
            persist_fn (optional gated persist of facts).
        中文：参数：max_messages（历史超过即压缩）；keep_recent（逐字保留的最近回合）；summarize_fn（默认确定性）；
            persist_fn（可选的门控事实持久化）。
        """
        self._max = max_messages
        self._keep = keep_recent
        self._summarize = summarize_fn
        self._persist = persist_fn

    def should_compress(self, messages: List[Message]) -> bool:
        """Whether the history is long enough to compress.

        EN: Args: messages. Returns: True if ``len(messages) > max_messages``.
        中文：参数：messages。返回：若 ``len(messages) > max_messages`` 则 True。
        """
        return len(messages) > self._max

    def compress(self, session_id: str, store: "SessionStore", hooks: "MemoryHooks") -> CompressionResult:
        """Fold old messages into a fact-preserving summary; best-effort gated persist.

        EN —
        Args: session_id; store (a ``SessionStore``); hooks (a ``MemoryHooks`` with ``on_pre_compress``).
        Returns: a ``CompressionResult``. Captures ``facts`` (failure-isolated), writes the summary via
        ``store.compact``, then best-effort ``persist_fn(facts)`` (a raised gate rejection is swallowed →
        ``persisted=False``; the summary is still written so the fact survives in-context).

        中文 —
        参数：session_id；store（``SessionStore``）；hooks（带 ``on_pre_compress`` 的 ``MemoryHooks``）。返回：
        ``CompressionResult``。捕获 ``facts``（失败隔离），经 ``store.compact`` 写摘要，再尽力 ``persist_fn(facts)``
        （抛出的门控拒绝被吞 → ``persisted=False``；摘要仍写入，使事实在上下文中存活）。
        """
        msgs = store.get_messages(session_id)
        if len(msgs) <= self._keep:
            return CompressionResult(compressed=False)
        old = msgs[: -self._keep] if self._keep > 0 else msgs
        try:
            facts = hooks.on_pre_compress(old) or ""
        except Exception:
            facts = ""
        summary = self._summarize(old, facts)
        store.compact(session_id, Message(Role.SYSTEM, content=summary), self._keep)
        persisted = False
        if self._persist is not None and facts.strip():
            try:
                persisted = bool(self._persist(facts))
            except Exception:
                persisted = False  # a gated-persist rejection must not crash the turn
        return CompressionResult(compressed=True, summary=summary, facts=facts, persisted=persisted)


__all__ = ["CompressionResult", "ContextCompressor", "default_summarize"]
