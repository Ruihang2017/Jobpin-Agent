"""Tests for the step-level tracer.

EN —
Confirms events are recorded in order with their kinds/data, and that JSONL
serialisation is one line per event.
中文 —
确认事件按顺序连同其类型/数据被记录，且 JSONL 序列化为每事件一行。
"""
import json
from jobpin_agent.core.tracing import Tracer


def test_events_recorded_in_order_with_kinds():
    """Events keep insertion order, kinds, payloads, and 0-based seq numbers.

    EN: Verifies ordering and that ``data`` kwargs are stored on the event.
    中文：验证顺序，以及 ``data`` 关键字参数被存于事件上。
    """
    t = Tracer()
    t.event("model_call", n=0)
    t.event("tool_call", name="echo")
    kinds = [e.kind for e in t.events]
    assert kinds == ["model_call", "tool_call"]
    assert t.events[1].data["name"] == "echo"
    assert [e.seq for e in t.events] == [0, 1]


def test_to_jsonl_is_one_line_per_event():
    """``to_jsonl`` emits exactly one JSON object per recorded event.

    EN: Confirms a single event serialises to a single parseable line.
    中文：确认单个事件序列化为单行可解析 JSON。
    """
    t = Tracer()
    t.event("turn_start")
    lines = t.to_jsonl().splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["kind"] == "turn_start"
