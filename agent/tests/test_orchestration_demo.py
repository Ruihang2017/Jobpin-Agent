"""Test for the §1.7 orchestration demo — the long-running hiring loop across simulated restarts.

EN — proves the demo exercises all three persistence contracts end-to-end over a file DB: cross-day
suspend/resume, crash recovery, and idempotent offer email (sent exactly once across the replay).
中文 — 证明该演示在文件 DB 上端到端演练全部三条持久化契约：跨天暂停/恢复、崩溃恢复、幂等 offer 邮件（含重放恰发一次）。
"""
from examples.orchestration_demo import run_demo


def test_demo_resumes_across_restarts_and_is_idempotent(tmp_path):
    """A fresh engine each phase recovers from disk; the loop completes; the offer email fires once.

    EN: recovered suspend + hitl states, DONE, 1 email, deduped, full transition history.
    中文：恢复 suspend + hitl 状态、DONE、1 封邮件、去重、完整转移历史。
    """
    out = run_demo(str(tmp_path / "demo.db"))
    assert out["recovered_suspended"] == "background_check"   # ② found suspended, resumed later
    assert out["recovered_hitl"] == "awaiting_review"         # ① recovered the HITL pause from disk
    assert out["final_status"].value == "done"
    assert out["email_sends"] == 1 and out["deduped"] is True  # ③ idempotent: sent once, replay deduped
    assert out["transitions"] == ["new", "screening", "background_check", "awaiting_review", "offer"]
