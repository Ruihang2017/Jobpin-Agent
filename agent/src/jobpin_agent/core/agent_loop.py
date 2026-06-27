"""The agent turn loop — the heart of the core (Layer A).

EN —
``Agent.run_turn`` runs one full turn synchronously: recall (via the memory
seam), assemble the system prompt, call the model, and — if the model asks for
tools — execute them and loop, until the model gives a final answer or a safety
limit stops it. Two design points the triple-review locked in: (1) per-turn
prefetch recall is injected as a fenced ``<memory-context>`` MESSAGE, never into
the frozen system-prompt snapshot slot, so the prefix stays stable (Key Invariant
#1); (2) the loop never mutates ``self.parts`` — a turn-local copy is built each
call. Design borrowed from Hermes ``conversation_loop.run_conversation`` and
rewritten lean (PRD §2.7).

中文 —
``Agent.run_turn`` 同步运行一个完整回合：召回（经记忆接缝）、装配系统提示、调用模型，若模型请求工具则执行
并循环，直到模型给出最终答复或安全上限将其停止。三方评审锁定的两个设计点：(1) 每回合的 prefetch 召回作为围栏
``<memory-context>`` 消息注入，绝不进入冻结的系统提示快照槽位，使前缀保持稳定（关键不变量 #1）；
(2) 循环绝不改动 ``self.parts``——每次调用构建回合局部副本。设计借鉴自 Hermes
``conversation_loop.run_conversation`` 并重写为精简版（PRD §2.7）。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from .hooks import MemoryHooks, NoOpHooks
from .messages import Message, ModelResponse, Role
from .model.provider import ModelProvider
from .session_store import SessionStore
from .system_prompt import SystemPromptParts, build_system_prompt
from .tools import ToolRegistry
from .tracing import Tracer


def _summarize_message(message: Message) -> dict:
    """Render a message as a compact, JSON-safe dict for tracing.

    EN —
    Args:
        message: The message to summarise.
    Returns:
        A dict with ``role`` and only the populated fields (``content`` /
        ``tool_calls`` / ``tool_result``), suitable for a trace payload.

    中文 —
    参数：
        message：要概述的消息。
    返回：
        含 ``role`` 及仅有内容的字段（``content`` / ``tool_calls`` / ``tool_result``）的 dict，适合作追踪负载。
    """
    summary: dict = {"role": message.role.value}
    if message.content:
        summary["content"] = message.content
    if message.tool_calls:
        summary["tool_calls"] = [{"name": c.name, "arguments": c.arguments} for c in message.tool_calls]
    if message.tool_result is not None:
        summary["tool_result"] = message.tool_result.content
    return summary


def _summarize_response(response: ModelResponse) -> dict:
    """Render a model response as a compact, JSON-safe dict for tracing.

    EN —
    Args:
        response: The model response to summarise.
    Returns:
        ``{"tool_calls": [...]}`` for a tool-call response, else ``{"text": ...}``.

    中文 —
    参数：
        response：要概述的模型响应。
    返回：
        工具调用响应为 ``{"tool_calls": [...]}``，否则为 ``{"text": ...}``。
    """
    if response.is_tool_call:
        return {"tool_calls": [{"name": c.name, "arguments": c.arguments} for c in response.tool_calls]}
    return {"text": response.text}


@dataclass
class TurnResult:
    """The outcome of one ``run_turn``.

    EN —
    Attributes:
        text: The model's final answer, or ``None`` if the turn was stopped.
        stopped: ``True`` if the safety limit (max tool rounds) ended the turn.
        messages: The full persisted message history after the turn.

    中文 —
    属性：
        text：模型的最终答复；若回合被停止则为 ``None``。
        stopped：若安全上限（最大工具轮数）结束了回合则为 ``True``。
        messages：回合后已持久化的完整消息历史。
    """

    text: str | None
    stopped: bool
    messages: list[Message] = field(default_factory=list)


class Agent:
    """A local agent that runs turns against a ``ModelProvider``.

    EN —
    Wires together a provider, a tool registry, a session store, a tracer, and
    the memory seam. It is provider-agnostic (sees only ``ModelProvider`` + the
    internal types) and carries no memory of its own in §1.1 (``NoOpHooks``).

    中文 —
    将 provider、工具注册表、会话存储、追踪器与记忆接缝连接起来。它是 provider 无关的（只接触
    ``ModelProvider`` 与内部类型），在 §1.1 自身不带记忆（``NoOpHooks``）。
    """

    def __init__(
        self,
        provider: ModelProvider,
        tools: ToolRegistry,
        session_store: SessionStore,
        tracer: Tracer | None = None,
        hooks: MemoryHooks | None = None,
        parts: SystemPromptParts | None = None,
        max_tool_iterations: int = 8,
    ) -> None:
        """Construct an agent.

        EN —
        Args:
            provider: The model backend (real or fake).
            tools: Tools the agent may call.
            session_store: Where turns are persisted.
            tracer: Step-level tracer (a fresh one is created if ``None``).
            hooks: Memory seam (``NoOpHooks`` if ``None``).
            parts: Static system-prompt sections (empty if ``None``). Treated as
                read-only by the loop.
            max_tool_iterations: Max tool rounds before stopping a turn.

        中文 —
        参数：
            provider：模型后端（真实或伪造）。
            tools：agent 可调用的工具。
            session_store：回合持久化位置。
            tracer：步骤级追踪器（为 ``None`` 时新建）。
            hooks：记忆接缝（为 ``None`` 时用 ``NoOpHooks``）。
            parts：静态系统提示章节（为 ``None`` 时为空）。循环将其视为只读。
            max_tool_iterations：停止回合前的最大工具轮数。
        """
        self.provider = provider
        self.tools = tools
        self.store = session_store
        self.tracer = tracer or Tracer()
        self.hooks = hooks or NoOpHooks()
        self.parts = parts or SystemPromptParts()
        self.max_tool_iterations = max_tool_iterations

    def _compose(self, history: list[Message], recall: str) -> list[Message]:
        """Build the message list sent to the model for this turn.

        EN —
        Builds a turn-local ``SystemPromptParts`` (never mutating ``self.parts``):
        the system prompt comes from the FROZEN-SNAPSHOT slot only (static per
        session; filled by §1.2). Per-turn ``recall`` is appended as a separate
        fenced ``<memory-context>`` message so the system-prompt prefix stays
        byte-stable (Key Invariant #1).
        Args:
            history: The session's prior messages.
            recall: Prefetch recall text (empty in §1.1).
        Returns:
            ``[system_prompt, <memory-context>?, *history]``.

        中文 —
        构建回合局部的 ``SystemPromptParts``（绝不改动 ``self.parts``）：系统提示仅来自冻结快照槽位
        （每会话静态；由 §1.2 填充）。每回合的 ``recall`` 作为单独的围栏 ``<memory-context>`` 消息追加，
        使系统提示前缀保持逐字节稳定（关键不变量 #1）。
        参数：
            history：会话的既往消息。
            recall：prefetch 召回文本（§1.1 为空）。
        返回：
            ``[系统提示, <memory-context>?, *历史]``。
        """
        parts = SystemPromptParts(
            org_policy=self.parts.org_policy,
            compliance=self.parts.compliance,
            role_permissions=self.parts.role_permissions,
            memory_snapshot=self.parts.memory_snapshot,
            provider_block=self.parts.provider_block,
            tools=self.tools.specs(),
        )
        messages = [Message(Role.SYSTEM, content=build_system_prompt(parts))]
        # Per-turn prefetch recall is a fenced <memory-context> MESSAGE (not the
        # system prompt), keeping the prefix stable (Key Invariant #1). Inert in
        # §1.1 (NoOpHooks returns ""); real recall arrives at §1.2/§1.3.
        if recall:
            messages.append(Message(Role.SYSTEM, content=f"<memory-context>\n{recall}\n</memory-context>"))
        return [*messages, *history]

    def run_turn(self, session_id: str, user_input: str) -> TurnResult:
        """Run one full turn end to end.

        EN —
        Flow: prefetch recall → append the user message → loop [assemble → model
        call → if tool calls: (stop if at the limit) execute + append results;
        else: append the answer, fire ``after_turn``, return]. Every step emits a
        trace event.
        Args:
            session_id: The session to run within (must already exist).
            user_input: The user's message text.
        Returns:
            A ``TurnResult`` with the final answer (or ``stopped=True``).

        中文 —
        流程：prefetch 召回 → 追加用户消息 → 循环 [装配 → 调模型 → 若有工具调用：（到上限则停止）执行并追加
        结果；否则：追加答复、触发 ``after_turn``、返回]。每步都发出一条追踪事件。
        参数：
            session_id：运行所在的会话（必须已存在）。
            user_input：用户消息文本。
        返回：
            含最终答复（或 ``stopped=True``）的 ``TurnResult``。
        """
        self.tracer.event("turn_start", session_id=session_id, user_input=user_input)
        recall = self.hooks.prefetch(user_input, session_id)  # per-turn fenced recall (no-op in §1.1)
        self.store.append_message(session_id, Message(Role.USER, content=user_input))
        iterations = 0
        while True:
            history = self.store.get_messages(session_id)
            sent = self._compose(history, recall)
            started = time.monotonic()
            response = self.provider.complete(sent, self.tools.specs())
            latency_ms = round((time.monotonic() - started) * 1000, 2)
            # Rich model_call event: the full messages sent, the response, tokens, latency.
            self.tracer.event(
                "model_call",
                iteration=iterations,
                request=[_summarize_message(m) for m in sent],
                response=_summarize_response(response),
                usage=response.usage,
                latency_ms=latency_ms,
            )
            if response.is_tool_call:
                if iterations >= self.max_tool_iterations:
                    self.tracer.event("turn_end", stopped=True, text=None)
                    return TurnResult(text=None, stopped=True, messages=self.store.get_messages(session_id))
                self.store.append_message(session_id, Message(Role.ASSISTANT, tool_calls=response.tool_calls))
                for call in response.tool_calls:
                    started = time.monotonic()
                    result = self.tools.execute(call)
                    self.tracer.event(
                        "tool_call",
                        name=call.name,
                        arguments=call.arguments,
                        result=result.content,
                        latency_ms=round((time.monotonic() - started) * 1000, 2),
                    )
                    self.store.append_message(session_id, Message(Role.TOOL, tool_result=result))
                iterations += 1
                continue
            self.store.append_message(session_id, Message(Role.ASSISTANT, content=response.text or ""))
            final = self.store.get_messages(session_id)
            self.hooks.after_turn(session_id, final)
            self.tracer.event("turn_end", stopped=False, text=response.text)
            return TurnResult(text=response.text, stopped=False, messages=final)
