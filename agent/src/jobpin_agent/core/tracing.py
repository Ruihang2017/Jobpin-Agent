"""Lightweight step-level tracing. Full Langfuse/OTel integration is §1.11."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class TraceEvent:
    seq: int
    kind: str
    data: dict
    at: float


class Tracer:
    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        self._events: list[TraceEvent] = []
        self._clock = clock or (lambda: 0.0)
        self._seq = 0

    def event(self, kind: str, **data: Any) -> None:
        self._events.append(TraceEvent(self._seq, kind, data, self._clock()))
        self._seq += 1

    @property
    def events(self) -> list[TraceEvent]:
        return list(self._events)

    def to_jsonl(self) -> str:
        return "\n".join(
            json.dumps({"seq": e.seq, "kind": e.kind, "data": e.data, "at": e.at}) for e in self._events
        )
