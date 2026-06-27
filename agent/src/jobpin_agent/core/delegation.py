"""Sub-agent delegation — let the agent hand a sub-task to a child agent.

EN —
``delegate`` runs a child ``Agent`` for one turn and returns its result to the
parent. It enforces Key Invariant #3: children run with ``skip_memory`` (their
own ``NoOpHooks``) and never persist sensitive memory; the parent observes the
child's output via ``on_delegation`` and adjudicates any writes (a no-op until
the Memory Subsystem exists). The child inherits the parent's prompt context
(org/compliance/role) and shares the parent's tools + session DB, and the child
session records its parent id for the §1.7 / audit causal chain. Design borrowed
from Hermes ``on_delegation``.

中文 —
``delegate`` 运行一个子 ``Agent`` 一个回合并把结果返回父代理。它落实关键不变量 #3：子代理以
``skip_memory`` 运行（各自的 ``NoOpHooks``），绝不持久化敏感记忆；父代理经 ``on_delegation`` 观察子代理输出
并审定写入（在记忆子系统就绪前为空操作）。子代理继承父代理的提示上下文（组织/合规/角色），共享父代理的工具与会话库，
且子会话记录其父 id 以用于 §1.7 / 审计因果链。设计借鉴自 Hermes ``on_delegation``。
"""
from __future__ import annotations

from dataclasses import dataclass

from .agent_loop import Agent
from .hooks import NoOpHooks
from .model.provider import ModelProvider


@dataclass
class DelegationResult:
    """The result of a delegated sub-task.

    EN —
    Attributes:
        text: The child's final answer (or ``None`` if its turn was stopped).
        child_session_id: The session id created for the child run.

    中文 —
    属性：
        text：子代理的最终答复（若其回合被停止则为 ``None``）。
        child_session_id：为子代理运行创建的会话 id。
    """

    text: str | None
    child_session_id: str


def delegate(
    parent: Agent,
    task: str,
    child_provider: ModelProvider,
    child_session_id: str | None = None,
    parent_session_id: str | None = None,
) -> DelegationResult:
    """Run a sub-task in a fresh child agent and return its result.

    EN —
    Builds a child ``Agent`` that shares the parent's tools, session store, tracer
    and prompt parts, but runs with ``NoOpHooks`` (skip_memory). Creates a child
    session (linked to ``parent_session_id`` for lineage), runs one turn, then
    notifies the parent via ``on_delegation``.
    Args:
        parent: The delegating agent (source of tools/store/tracer/parts/hooks).
        task: The sub-task prompt for the child.
        child_provider: The model backend the child uses (its own provider).
        child_session_id: Optional explicit id for the child session.
        parent_session_id: The parent's session id, recorded as the child's lineage.
    Returns:
        A ``DelegationResult`` with the child's answer and session id.

    中文 —
    构建一个共享父代理工具、会话存储、追踪器与提示 parts 的子 ``Agent``，但以 ``NoOpHooks``（skip_memory）运行。
    创建子会话（经 ``parent_session_id`` 关联血缘），运行一个回合，再经 ``on_delegation`` 通知父代理。
    参数：
        parent：委派方 agent（工具/存储/追踪器/parts/钩子的来源）。
        task：给子代理的子任务提示。
        child_provider：子代理使用的模型后端（其自有 provider）。
        child_session_id：子会话的可选显式 id。
        parent_session_id：父代理会话 id，记录为子代理的血缘。
    返回：
        含子代理答复与会话 id 的 ``DelegationResult``。
    """
    # Child shares the parent's tools + session DB + prompt context (org / compliance /
    # role), but runs skip_memory (NoOpHooks). parent_session_id records lineage for
    # the §1.7 / audit causal chain.
    child = Agent(
        provider=child_provider,
        tools=parent.tools,
        session_store=parent.store,
        tracer=parent.tracer,
        hooks=NoOpHooks(),  # skip_memory: child writes no sensitive memory
        parts=parent.parts,
        max_tool_iterations=parent.max_tool_iterations,
    )
    sid = parent.store.create_session(child_session_id, parent_id=parent_session_id)
    parent.tracer.event("delegation", task=task, child_session_id=sid)
    result = child.run_turn(sid, task)
    parent.hooks.on_delegation(task, result.text or "", sid)
    return DelegationResult(text=result.text, child_session_id=sid)
