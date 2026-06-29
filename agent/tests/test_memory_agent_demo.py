"""Test for the §1.3 offline memory-agent demo.

EN — Asserts the demo shows the three §1.3 outcomes (snapshot in prompt, fenced
recall via the seam, sync visible after the turn). 中文 — 断言 demo 展示三个 §1.3 结果
（快照入提示、经接缝的围栏召回、回合后 sync 可见）。
"""
from examples.memory_agent_demo import run_demo


def test_demo_shows_snapshot_recall_and_sync():
    """The demo proves the loop closes through the memory seam, offline.

    EN: org in prompt; fenced recall; recall in prompt; turn synced. 中文：org 入提示；围栏召回；召回入提示；回合已同步。
    """
    out = run_demo()
    assert out["system_prompt_has_org"] is True
    assert "[System note:" in out["prefetch_inner"] and "cand_7f3a" in out["prefetch_inner"]
    assert "<memory-context>" not in out["prefetch_inner"]  # inner block has no outer tags
    assert out["recall_in_prompt"] is True
    assert out["synced_after_turn"] is True
    assert out["answer"]
