"""Runnable §1.7 demo — a long-running hiring loop that survives "restarts" and never double-acts.

EN —
Demonstrates the Layer B orchestration skeleton **end to end, standalone** — no agent, no LLM, no
connectors needed (those are M3 / §1.10 / §1.11). One hiring instance is driven across **four separate
"process lifetimes"**: between each phase the engine + store are dropped and a **fresh ``ProcessEngine``
is built over the same SQLite file** — exactly what happens when the program is killed and restarted, or
the loop pauses overnight. It exercises all three persistence contracts in one story:
  ① crash recovery (a fresh process resumes from the persisted state),
  ② cross-day pause/resume (SUSPENDED awaiting an external event, resumed later),
  ③ external side-effect idempotency (the offer email is sent exactly once, even on a replay).

HONEST SCOPE: the states (screening / background_check / awaiting_review / offer) and the "send offer
email" side effect are **illustrative stand-ins** — the real recruitment states are Phase 1 M3, the real
agent reasoning at each step is §1.11, and the real email/calendar connector is §1.10. What is REAL here
is the orchestration itself: durable state, recovery, HITL pause, and idempotent side effects. The "restart"
is a fresh engine over the same committed SQLite file (the same mechanism that works across real OS
processes), not a mid-write kill.

Run from ``agent/``: ``python examples/orchestration_demo.py``

中文 —
**端到端、独立**演示 Layer B 编排骨架——无需 agent、LLM 或连接器（那些是 M3 / §1.10 / §1.11）。一个招聘实例被驱动经
**四段独立“进程生命周期”**：每阶段之间丢弃引擎与存储，并在**同一 SQLite 文件上新建 ``ProcessEngine``**——正是程序被
杀死重启、或 loop 跨夜暂停时发生之事。它在一个故事中演练全部三条持久化契约：① 崩溃恢复（新进程从持久状态恢复）；
② 跨天暂停/恢复（SUSPENDED 等外部事件，稍后恢复）；③ 外部副作用幂等（offer 邮件恰发一次，即使重放）。

诚实范围：状态（screening / background_check / awaiting_review / offer）与“发 offer 邮件”副作用是**示意替身**——真实
招聘状态是第一阶段 M3，每步真实 agent 推理是 §1.11，真实邮件/日历连接器是 §1.10。此处**真实**的是编排本身：持久状态、
恢复、HITL 暂停与幂等副作用。“重启”是同一已提交 SQLite 文件上的新引擎（与跨真实 OS 进程相同的机制），非写入中途杀死。
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Allow `python agent/examples/orchestration_demo.py` without setting PYTHONPATH.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpin_agent.orchestration.idempotency import IdempotencyStore
from jobpin_agent.orchestration.recovery import recover
from jobpin_agent.orchestration.state_machine import ProcessDefinition, ProcessEngine, Status
from jobpin_agent.orchestration.store import OrchestrationStore

INSTANCE_ID = "req_812:cand_7f3a"
OFFER_EMAIL_KEY = "email:req_812:cand_7f3a:offer"


def hiring_definition() -> ProcessDefinition:
    """The illustrative hiring process: new → screening → background_check → awaiting_review → offer.

    EN —
    ``background_check`` is a SUSPEND state (awaiting an external event — the check result); ``awaiting_review``
    is a HITL state (awaiting a human hiring decision); ``offer`` is terminal. Real recruitment states are M3.
    中文 —
    ``background_check`` 为 SUSPEND 状态（等外部事件——背调结果）；``awaiting_review`` 为 HITL 状态（等人工招聘决定）；
    ``offer`` 为终止。真实招聘状态在 M3。
    """
    return ProcessDefinition(
        process_type="hiring",
        initial_state="new",
        transitions={
            "new": {"screening"},
            "screening": {"background_check"},
            "background_check": {"awaiting_review"},
            "awaiting_review": {"offer"},
            "offer": set(),
        },
        suspend_states={"background_check"},
        hitl_states={"awaiting_review"},
        terminal_states={"offer"},
    )


def run_demo(db_path: str) -> dict:
    """Drive one hiring instance across four fresh-engine "restarts" over the same SQLite file.

    EN —
    Args: db_path (a FILE path so state survives across the simulated restarts; the test passes a tmp file).
    Returns: a dict for assertions + a narration ``lines`` list — keys: ``recovered_suspended`` (state found
    by the day-3 process), ``recovered_hitl`` (state found by the day-5 process), ``final_status``,
    ``email_sends`` (must be 1 — idempotent), ``deduped`` (the replay was skipped), ``transitions`` (the
    audited to-states). Each phase builds a NEW ``OrchestrationStore`` + ``ProcessEngine`` over ``db_path``,
    proving recovery from disk (not in-memory carry-over).

    中文 —
    参数：db_path（文件路径，使状态跨模拟重启存活；测试传 tmp 文件）。返回：用于断言的 dict + 叙述 ``lines`` 列表——键：
    ``recovered_suspended``（第 3 天进程发现的状态）、``recovered_hitl``（第 5 天进程发现的状态）、``final_status``、
    ``email_sends``（须为 1——幂等）、``deduped``（重放被跳过）、``transitions``（被审计的 to-state）。每阶段在 ``db_path``
    上新建 ``OrchestrationStore`` + ``ProcessEngine``，证明从磁盘恢复（非内存延续）。
    """
    if db_path != ":memory:" and os.path.exists(db_path):
        os.remove(db_path)  # fresh demo each run
    defn = hiring_definition()
    lines: list[str] = []
    sends = {"count": 0}

    def send_offer_email() -> str:
        """The illustrative external side effect (a real SMTP/connector is §1.10).

        EN: increments a send counter, returns a fake message id. 中文：递增发送计数，返回伪消息 id。
        """
        sends["count"] += 1
        return f"smtp-msgid-{sends['count']}"

    def fresh_engine() -> ProcessEngine:
        """Build a NEW engine over the same DB file — a simulated process restart.

        EN: Returns: a ProcessEngine reading the persisted state from disk. 中文：返回：从磁盘读持久状态的 ProcessEngine。
        """
        return ProcessEngine(OrchestrationStore(db_path), defn)

    # ── Day 1 (process #1): open the loop, screen, then SUSPEND awaiting the background check ──
    e1 = fresh_engine()
    e1.start(INSTANCE_ID, context_ref="candidate=cand_7f3a; req=812")
    e1.transition(INSTANCE_ID, "screening", trigger="sourced → screen")
    e1.suspend(INSTANCE_ID, to_state="background_check", trigger="await external background-check result")
    lines.append("Day 1  [process #1]  started → screening → SUSPENDED awaiting background check, then exit.")

    # ── Day 3 (process #2, fresh engine over the same file): recover, the check arrives, pause for a human ──
    e2 = fresh_engine()
    pending = recover(e2.store)
    recovered_suspended = pending[0].current_state if pending else None
    lines.append(f"Day 3  [process #2]  recovered from disk: {[(i.instance_id, i.status.value, i.current_state) for i in pending]}")
    e2.transition(INSTANCE_ID, "awaiting_review", trigger="background check cleared")  # → AWAITING_HITL
    lines.append("       background check cleared → AWAITING_HITL (a recruiter must decide), then exit.")

    # ── Day 5 (process #3, fresh engine): recover the HITL pause, human approves, send the offer email once ──
    e3 = fresh_engine()
    pending = recover(e3.store)
    recovered_hitl = pending[0].current_state if pending else None
    lines.append(f"Day 5  [process #3]  recovered from disk: {[(i.instance_id, i.status.value, i.current_state) for i in pending]}")
    e3.resume_hitl(INSTANCE_ID, to_state="offer", decision="approve", actor="recruiter:alice")
    result, executed = IdempotencyStore(e3.store).run_once(OFFER_EMAIL_KEY, send_offer_email)
    lines.append(f"       recruiter approved → offer (DONE). Offer email: sent={executed} id={result}.")

    # ── A duplicate run (process #4, fresh engine): replay the offer-email effect → must be deduped ──
    e4 = fresh_engine()
    result2, executed2 = IdempotencyStore(e4.store).run_once(OFFER_EMAIL_KEY, send_offer_email)
    lines.append(f"Replay [process #4]  re-ran the offer-email effect → sent={executed2} (deduped; id still {result2}).")

    final = fresh_engine().store.load_instance(INSTANCE_ID)
    transitions = [t.to_state for t in fresh_engine().store.transitions_for(INSTANCE_ID)]
    lines.append(f"Audit  transition history (to-states): {transitions}")
    lines.append(f"Result final status={final.status.value}; offer emails actually sent={sends['count']} (idempotent).")

    return {
        "lines": lines,
        "recovered_suspended": recovered_suspended,
        "recovered_hitl": recovered_hitl,
        "final_status": final.status,
        "email_sends": sends["count"],
        "deduped": (executed is True and executed2 is False),
        "transitions": transitions,
    }


def main() -> None:  # pragma: no cover
    """Run the demo over a temp-dir SQLite file and narrate each phase.

    EN: Returns: None (prints the narration + a footer). 中文：返回：None（打印叙述 + 页脚）。
    """
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    db_path = str(Path(tempfile.gettempdir()) / "jobpin_orchestration_demo.db")
    print("§1.7 Layer B orchestration — a long-running hiring loop across simulated restarts")
    print(f"(durable state in {db_path}; each phase is a FRESH engine over that same file)\n")
    out = run_demo(db_path)
    for line in out["lines"]:
        print(line)
    print(f"\n[contracts shown: ① crash recovery (recovered at {out['recovered_hitl']}), "
          f"② cross-day pause/resume (suspended at {out['recovered_suspended']}, resumed later), "
          f"③ side-effect idempotency (offer emails sent = {out['email_sends']}, deduped = {out['deduped']})]")


if __name__ == "__main__":  # pragma: no cover
    main()
