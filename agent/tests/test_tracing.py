import json
from jobpin_agent.core.tracing import Tracer


def test_events_recorded_in_order_with_kinds():
    t = Tracer()
    t.event("model_call", n=0)
    t.event("tool_call", name="echo")
    kinds = [e.kind for e in t.events]
    assert kinds == ["model_call", "tool_call"]
    assert t.events[1].data["name"] == "echo"
    assert [e.seq for e in t.events] == [0, 1]


def test_to_jsonl_is_one_line_per_event():
    t = Tracer()
    t.event("turn_start")
    lines = t.to_jsonl().splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["kind"] == "turn_start"
