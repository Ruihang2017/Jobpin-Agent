"""Step-level tracing — make each step of a turn observable.

EN —
Records an ordered list of events (model calls, tool calls, delegations, turn
boundaries) so a turn can be inspected after the fact. This is a deliberately
tiny, local tracer; the full observability stack (Langfuse / OpenTelemetry,
locally deployable) arrives at §1.11. The clock is injected so tests are
deterministic and so we never call a non-deterministic time source implicitly.

中文 —
记录有序的事件列表（模型调用、工具调用、委派、回合边界），使一个回合可在事后检视。这是刻意精简的本地
追踪器；完整可观测栈（Langfuse / OpenTelemetry，可本地部署）在 §1.11 引入。时钟以注入方式提供，
使测试具确定性，并避免隐式调用非确定性时间源。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class TraceEvent:
    """One recorded step in a turn.

    EN —
    Attributes:
        seq: Monotonic 0-based order index within a tracer.
        kind: Event kind (e.g. ``"model_call"``, ``"tool_call"``, ``"turn_end"``).
        data: Arbitrary structured payload for the event.
        at: Timestamp from the injected clock.

    中文 —
    属性：
        seq：单个追踪器内从 0 起的单调顺序索引。
        kind：事件类型（如 ``"model_call"``、``"tool_call"``、``"turn_end"``）。
        data：事件的任意结构化负载。
        at：来自注入时钟的时间戳。
    """

    seq: int
    kind: str
    data: dict
    at: float


class Tracer:
    """Collects ordered ``TraceEvent`` records for one run.

    EN —
    Append-only and in-memory; ``to_jsonl`` serialises for inspection or a sink.

    中文 —
    仅追加、内存内；``to_jsonl`` 序列化以供检视或落地。
    """

    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        """Create a tracer.

        EN —
        Args:
            clock: Zero-arg callable returning a float timestamp. Defaults to a
                constant ``0.0`` clock (deterministic for tests); pass
                ``time.monotonic`` in real use.

        中文 —
        参数：
            clock：返回 float 时间戳的零参可调用对象。默认为常量 ``0.0`` 时钟（便于测试确定性）；
                实际使用时传入 ``time.monotonic``。
        """
        self._events: list[TraceEvent] = []
        self._clock = clock or (lambda: 0.0)
        self._seq = 0

    def event(self, kind: str, **data: Any) -> None:
        """Record one event.

        EN —
        Args:
            kind: The event kind.
            **data: Arbitrary structured fields stored on the event.

        中文 —
        参数：
            kind：事件类型。
            **data：存储在事件上的任意结构化字段。
        """
        self._events.append(TraceEvent(self._seq, kind, data, self._clock()))
        self._seq += 1

    @property
    def events(self) -> list[TraceEvent]:
        """All recorded events, in order.

        EN —
        Returns:
            A new list copy of the events (callers cannot mutate internal state).

        中文 —
        返回：
            事件的新列表副本（调用方无法改动内部状态）。
        """
        return list(self._events)

    def to_jsonl(self) -> str:
        """Serialise the events as JSON Lines.

        EN —
        Returns:
            One JSON object per line (``seq``/``kind``/``data``/``at``); empty
            string if there are no events.

        中文 —
        返回：
            每行一个 JSON 对象（``seq``/``kind``/``data``/``at``）；无事件时返回空字符串。
        """
        return "\n".join(
            json.dumps({"seq": e.seq, "kind": e.kind, "data": e.data, "at": e.at}) for e in self._events
        )
