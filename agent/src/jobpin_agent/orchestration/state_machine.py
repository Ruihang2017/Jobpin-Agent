"""The Layer B state machine — declarative process definition + engine (§1.7).

EN —
A lightweight, in-house business-process state machine. A ``ProcessDefinition`` declares the legal states
and transitions of a process type (plus which states are HITL / suspend / terminal); a ``ProcessEngine``
drives instances against that definition — validating every transition, persisting the instance, and
appending an auditable transition to the history. Illegal (undeclared) transitions are rejected. This is
the skeleton: a toy process exercises it now; the real recruitment states are §M3.

The declared definition IS the auditable process contract (compliance needs "every step auditable", and
auditing depends on the persisted state history). The engine takes its store by injection, so it does not
import the store (no cycle); the store imports these dataclasses.

中文 —
轻量、自建的业务流程状态机。``ProcessDefinition`` 声明某流程类型的合法状态与转移（及哪些状态为 HITL / 挂起 / 终止）；
``ProcessEngine`` 依该定义驱动实例——校验每次转移、持久化实例，并向历史追加可审计的转移。非法（未声明）转移被拒。这是
骨架：当前以玩具流程演练；真实招聘状态在 M3。

声明的定义即可审计的流程契约（合规要求“每步可审计”，而审计依赖持久化的状态历史）。引擎以注入方式接收 store，故不导入
store（无环）；store 导入这些数据类。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Dict, Set


class Status(str, Enum):
    """The lifecycle status of a process instance (Plan §1.7).

    EN: RUNNING (active) / SUSPENDED (awaiting an external event) / AWAITING_HITL (awaiting a human
        decision) / DONE / FAILED (terminal). 中文：运行 / 挂起（等外部事件）/ 等待人工（等人工决定）/ 完成 / 失败（终止）。
    """

    RUNNING = "running"
    SUSPENDED = "suspended"
    AWAITING_HITL = "awaiting_hitl"
    DONE = "done"
    FAILED = "failed"


class IllegalTransition(Exception):
    """Raised when a transition is not declared by the ``ProcessDefinition`` (the guardrail).

    EN: an undeclared from→to (or an unknown instance) is rejected. 中文：未声明的 from→to（或未知实例）被拒绝。
    """


@dataclass
class ProcessInstance:
    """A persisted process instance — the crash-recovery load anchor (Plan §1.7).

    EN: Attributes: instance_id; process_type; current_state; status; context_ref (opaque pointer to the
        session / memory / entity); updated_at (ISO-8601 UTC). 中文：属性：instance_id；process_type；
        current_state；status；context_ref（指向会话/记忆/实体的不透明指针）；updated_at（ISO-8601 UTC）。
    """

    instance_id: str
    process_type: str
    current_state: str
    status: Status
    context_ref: str = ""
    updated_at: str = ""


@dataclass
class Transition:
    """One append-only state-transition record — the auditable history (Plan §1.7).

    EN: Attributes: instance_id; from_state; to_state; trigger (what caused it); at (ISO-8601 UTC); actor.
    中文：属性：instance_id；from_state；to_state；trigger（触发原因）；at（ISO-8601 UTC）；actor。
    """

    instance_id: str
    from_state: str
    to_state: str
    trigger: str
    at: str
    actor: str


@dataclass
class ProcessDefinition:
    """Declares a process type's legal states + transitions + state classes (the auditable contract).

    EN —
    Attributes: process_type; initial_state; transitions (``{from_state: {allowed to_states}}``);
    hitl_states / suspend_states / terminal_states (classify the resulting ``Status``). ``is_legal`` and
    ``status_for`` drive the engine.

    中文 —
    属性：process_type；initial_state；transitions（``{from_state: {允许的 to_states}}``）；
    hitl_states / suspend_states / terminal_states（决定结果 ``Status`` 的分类）。``is_legal`` 与 ``status_for`` 驱动引擎。
    """

    process_type: str
    initial_state: str
    transitions: Dict[str, Set[str]]
    hitl_states: Set[str] = field(default_factory=set)
    suspend_states: Set[str] = field(default_factory=set)
    terminal_states: Set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        """Validate the state-class sets are disjoint (a state can't be two of hitl/suspend/terminal).

        EN: Raises ValueError on overlap so a misconfiguration fails loudly (``status_for`` would otherwise
            resolve it by silent precedence). 中文：集合重叠时抛 ValueError，使配置错误显式失败（否则 ``status_for`` 会按
            静默优先级解析）。
        """
        overlap = ((self.terminal_states & self.hitl_states)
                   | (self.terminal_states & self.suspend_states)
                   | (self.hitl_states & self.suspend_states))
        if overlap:
            raise ValueError(f"ProcessDefinition state-class overlap (hitl/suspend/terminal): {sorted(overlap)}")

    def is_legal(self, from_state: str, to_state: str) -> bool:
        """Whether ``from_state -> to_state`` is a declared transition.

        EN: Args: from_state; to_state. Returns: True if declared. 中文：参数：from_state；to_state。返回：声明则 True。
        """
        return to_state in self.transitions.get(from_state, set())

    def status_for(self, state: str) -> Status:
        """Map a state to its lifecycle ``Status`` by its declared class.

        EN: Args: state. Returns: DONE if terminal, AWAITING_HITL if hitl, SUSPENDED if suspend, else RUNNING.
        中文：参数：state。返回：终止→DONE，hitl→AWAITING_HITL，挂起→SUSPENDED，否则 RUNNING。
        """
        if state in self.terminal_states:
            return Status.DONE
        if state in self.hitl_states:
            return Status.AWAITING_HITL
        if state in self.suspend_states:
            return Status.SUSPENDED
        return Status.RUNNING


def _utcnow() -> str:
    """Return the current UTC time as an ISO-8601 string (the engine's default clock).

    EN: Returns: ISO-8601 UTC. 中文：返回：ISO-8601 UTC。
    """
    return datetime.now(timezone.utc).isoformat()


class ProcessEngine:
    """Drives process instances against a ``ProcessDefinition`` — validate, persist, log (Plan §1.7).

    EN —
    Construct with a store (injected — duck-typed ``OrchestrationStore``), a definition, and an optional
    clock. Every state change goes through ``transition`` (validated + persisted + logged); ``start`` opens
    an instance at the initial state; ``await_hitl`` / ``suspend`` / ``resume_hitl`` / ``resume`` are
    intent-named sugar over ``transition`` (the resulting status comes from the definition's classification
    of the to-state); ``fail`` sets the terminal FAILED status.

    中文 —
    用 store（注入——鸭子类型 ``OrchestrationStore``）、定义与可选时钟构造。每次状态变更都经 ``transition``（校验 + 持久化 +
    记录）；``start`` 在初始状态开启实例；``await_hitl`` / ``suspend`` / ``resume_hitl`` / ``resume`` 为 ``transition`` 的
    意图命名糖（结果状态来自定义对 to-state 的分类）；``fail`` 设置终止 FAILED 状态。
    """

    def __init__(self, store, definition: ProcessDefinition, *, clock: Callable[[], str] = _utcnow) -> None:
        """Wire the engine to a store + a process definition.

        EN: Args: store (an ``OrchestrationStore``); definition; clock (default UTC now — inject for determinism).
        中文：参数：store（``OrchestrationStore``）；definition；clock（默认 UTC now——为确定性可注入）。
        """
        self.store = store
        self.definition = definition
        self._clock = clock

    def start(self, instance_id: str, *, context_ref: str = "", actor: str = "system") -> ProcessInstance:
        """Open a new instance at the definition's initial state (logs the ``start`` transition).

        EN: Args: instance_id; context_ref; actor. Returns: the new ``ProcessInstance`` (status RUNNING).
            Raises: ``IllegalTransition`` if the instance_id already exists (no silent re-start of a live process).
        中文：参数：instance_id；context_ref；actor。返回：新 ``ProcessInstance``（状态 RUNNING）。
            抛出：若 instance_id 已存在则 ``IllegalTransition``（不静默重启运行中的流程）。
        """
        if self.store.load_instance(instance_id) is not None:
            raise IllegalTransition(f"instance {instance_id!r} already exists (cannot re-start)")
        now = self._clock()
        inst = ProcessInstance(instance_id, self.definition.process_type, self.definition.initial_state,
                               Status.RUNNING, context_ref=context_ref, updated_at=now)
        self.store.apply(inst, Transition(instance_id, "", self.definition.initial_state, "start", now, actor))
        return inst

    def transition(self, instance_id: str, to_state: str, *, trigger: str, actor: str = "system") -> ProcessInstance:
        """Validate + apply a state transition; persist the instance and append the history record.

        EN —
        Args: instance_id; to_state; trigger (why); actor (who). Returns: the updated ``ProcessInstance``
        (status from ``definition.status_for(to_state)``). Raises: ``IllegalTransition`` if the instance is
        unknown or ``from_state -> to_state`` is not declared.

        中文 —
        参数：instance_id；to_state；trigger（为何）；actor（谁）。返回：更新后的 ``ProcessInstance``（状态取自
        ``definition.status_for(to_state)``）。抛出：实例未知或 ``from_state -> to_state`` 未声明时 ``IllegalTransition``。
        """
        inst = self.store.load_instance(instance_id)
        if inst is None:
            raise IllegalTransition(f"unknown instance {instance_id!r}")
        if not self.definition.is_legal(inst.current_state, to_state):
            raise IllegalTransition(f"{inst.current_state!r} -> {to_state!r} is not a declared transition")
        now = self._clock()
        from_state = inst.current_state
        inst.current_state = to_state
        inst.status = self.definition.status_for(to_state)
        inst.updated_at = now
        self.store.apply(inst, Transition(instance_id, from_state, to_state, trigger, now, actor))  # atomic (M1)
        return inst

    def await_hitl(self, instance_id: str, *, to_state: str, trigger: str, actor: str = "system") -> ProcessInstance:
        """Transition to a HITL state (the process pauses for a human decision).

        EN: Args: instance_id; to_state (must be a declared hitl_state); trigger; actor. Returns: the
            instance (AWAITING_HITL). Raises: ``IllegalTransition`` if ``to_state`` is not a hitl_state
            (so the method's name can't lie about the resulting status).
        中文：参数：instance_id；to_state（须为声明的 hitl_state）；trigger；actor。返回：实例（AWAITING_HITL）。
            抛出：若 ``to_state`` 非 hitl_state 则 ``IllegalTransition``（使方法名不与结果状态相悖）。
        """
        if to_state not in self.definition.hitl_states:
            raise IllegalTransition(f"{to_state!r} is not a declared hitl_state")
        return self.transition(instance_id, to_state, trigger=trigger, actor=actor)

    def resume_hitl(self, instance_id: str, *, to_state: str, decision: str, actor: str = "system") -> ProcessInstance:
        """Resume from a HITL state after a human decision.

        EN: Args: instance_id; to_state; decision (recorded in the trigger); actor. Returns: the instance.
        中文：参数：instance_id；to_state；decision（记入 trigger）；actor。返回：实例。
        """
        return self.transition(instance_id, to_state, trigger=f"hitl:{decision}", actor=actor)

    def suspend(self, instance_id: str, *, to_state: str, trigger: str, actor: str = "system") -> ProcessInstance:
        """Suspend to await an external event (logical — no wall-clock assumption).

        EN: Args: instance_id; to_state (must be a declared suspend_state); trigger; actor. Returns: the
            instance (SUSPENDED). Raises: ``IllegalTransition`` if ``to_state`` is not a suspend_state.
        中文：参数：instance_id；to_state（须为声明的 suspend_state）；trigger；actor。返回：实例（SUSPENDED）。
            抛出：若 ``to_state`` 非 suspend_state 则 ``IllegalTransition``。
        """
        if to_state not in self.definition.suspend_states:
            raise IllegalTransition(f"{to_state!r} is not a declared suspend_state")
        return self.transition(instance_id, to_state, trigger=trigger, actor=actor)

    def resume(self, instance_id: str, *, to_state: str, trigger: str, actor: str = "system") -> ProcessInstance:
        """Resume from a suspended state when the awaited event arrives.

        EN: Args: instance_id; to_state; trigger; actor. Returns: the instance.
        中文：参数：instance_id；to_state；trigger；actor。返回：实例。
        """
        return self.transition(instance_id, to_state, trigger=trigger, actor=actor)

    def fail(self, instance_id: str, *, reason: str, actor: str = "system") -> ProcessInstance:
        """Mark an instance FAILED (unrecoverable error) and log the terminal transition (atomic).

        EN —
        FAILED is a *status* that overlays any state (Plan §1.7's ``[any] → failed``), so — by design — this
        is the one path that intentionally **bypasses** the declarative ``is_legal`` guardrail (forcing every
        definition to declare ``→failed`` from every state would be noise). It writes a self-referential
        history record (``from == to``, ``trigger=fail:<reason>``) atomically via ``apply``.
        Args: instance_id; reason; actor. Returns: the instance (FAILED). Raises: ``IllegalTransition`` if the
        instance is unknown or already terminal (DONE/FAILED — do not overwrite a terminal outcome).

        中文 —
        FAILED 是覆盖任意状态的*状态*（计划 §1.7 的 ``[any] → failed``），故按设计这是唯一刻意**绕过**声明式 ``is_legal``
        守卫的路径（要求每个定义从每个状态都声明 ``→failed`` 是噪音）。经 ``apply`` 原子写一条自指历史（``from == to``，
        ``trigger=fail:<reason>``）。参数：instance_id；reason；actor。返回：实例（FAILED）。抛出：实例未知或已终止
        （DONE/FAILED——不覆盖终止结局）时 ``IllegalTransition``。
        """
        inst = self.store.load_instance(instance_id)
        if inst is None:
            raise IllegalTransition(f"unknown instance {instance_id!r}")
        if inst.status in (Status.DONE, Status.FAILED):
            raise IllegalTransition(f"instance {instance_id!r} is already terminal ({inst.status.value})")
        now = self._clock()
        from_state = inst.current_state
        inst.status = Status.FAILED
        inst.updated_at = now
        self.store.apply(inst, Transition(instance_id, from_state, from_state, f"fail:{reason}", now, actor))
        return inst


__all__ = ["Status", "IllegalTransition", "ProcessInstance", "Transition", "ProcessDefinition", "ProcessEngine"]
