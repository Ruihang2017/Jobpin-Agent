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


def test_at_most_once_gap_a_crash_before_done_is_not_resent():
    """The documented at-most-once boundary: if the effect raises after the pending claim, a replay skips.

    EN — the key stays 'pending', so a replay returns (result="", executed=False) and does NOT re-run
    (favours never-double-send; the un-sent effect is the disclosed trade-off). 中文 — 键保持 'pending'，故重放返回
    (result="", executed=False) 且**不**重跑（偏向绝不重发；未发出的副作用是已披露的权衡）。
    """
    store = OrchestrationStore()
    idem = IdempotencyStore(store)
    key = "email:req_812:cand_7f3a:offer"

    def boom():
        raise RuntimeError("crash after claim, before done")

    try:
        idem.run_once(key, boom)
    except RuntimeError:
        pass
    assert store.idem_get(key) == {"status": "pending", "result": ""}  # claimed, never completed
    calls = []
    result, executed = idem.run_once(key, lambda: calls.append(1) or "now-sent")
    assert executed is False and result == "" and calls == []          # replay skips — not re-run


def test_concurrent_claim_loser_skips():
    """A racer that lost the claim (key already pending) skips without executing (M2 guard).

    EN: simulate the race by pre-claiming via idem_begin. 中文：用 idem_begin 预登记模拟竞态。
    """
    store = OrchestrationStore()
    store.idem_begin("k", "t0")                       # another worker claimed it first
    calls = []
    result, executed = IdempotencyStore(store).run_once("k", lambda: calls.append(1) or "x")
    assert executed is False and calls == []
