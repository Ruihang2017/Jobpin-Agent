"""Test for the runnable demo.

EN —
Confirms the offline demo exercises all three paths (plain / tool / delegation)
and records trace events.
中文 —
确认离线演示演练三条路径（纯文本 / 工具 / 委派）并记录追踪事件。
"""
from examples.demo_turn import run_demo


def test_demo_runs_offline_and_exercises_all_paths():
    """``run_demo`` returns the expected plain/tool/delegation results offline.

    EN: With the default FakeProvider, the three outputs are deterministic and
    at least one trace event is recorded.
    中文：使用默认 FakeProvider 时，三个输出确定，且至少记录一条追踪事件。
    """
    out = run_demo()
    assert out["plain"] == "hello"
    assert "X" in out["tool"]
    assert out["delegation"] == "child-done"
    assert out["trace_events"] > 0
