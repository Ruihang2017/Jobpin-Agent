"""Tests for ``orchestration/idempotency.py`` — run-once dedup + restart-safety.

EN — run_once executes the effect once and dedups a retry; a replay after a simulated restart (fresh
store over the same file) does not re-send. 中文 — run_once 执行一次并去重重试；模拟重启（同一文件上新建存储）后的重放
不重发。
"""
from jobpin_agent.orchestration.idempotency import IdempotencyStore
from jobpin_agent.orchestration.store import OrchestrationStore


def test_run_once_executes_once_and_dedups():
    """The effect runs once; a second call with the same key is deduped (executed=False).

    EN. 中文。
    """
    idem = IdempotencyStore(OrchestrationStore())
    calls = []

    def send():
        calls.append(1)
        return "sent-id-1"

    r1, ex1 = idem.run_once("interview:req_812:cand_7f3a:slot_3", send)
    r2, ex2 = idem.run_once("interview:req_812:cand_7f3a:slot_3", send)
    assert ex1 is True and r1 == "sent-id-1"
    assert ex2 is False and len(calls) == 1


def test_replay_after_restart_does_not_resend(tmp_path):
    """A replay over a fresh store on the same DB file does not re-run the effect.

    EN: restart-safe dedup. 中文：重启安全去重。
    """
    db = str(tmp_path / "orch.db")
    calls = []

    def send():
        calls.append(1)
        return "ok"

    IdempotencyStore(OrchestrationStore(db)).run_once("email:req_812:cand_7f3a:offer", send)
    _, ex = IdempotencyStore(OrchestrationStore(db)).run_once("email:req_812:cand_7f3a:offer", send)
    assert ex is False and len(calls) == 1
