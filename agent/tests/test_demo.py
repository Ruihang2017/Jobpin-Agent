from examples.demo_turn import run_demo


def test_demo_runs_offline_and_exercises_all_paths():
    out = run_demo()
    assert out["plain"] == "hello"
    assert "X" in out["tool"]
    assert out["delegation"] == "child-done"
    assert out["trace_events"] > 0
