"""Test for the memory inspect demo (§1.2).

EN — Verifies the offline demo builds a store, exposes the frozen snapshot, and rejects drift.
中文 — 验证离线演示能建库、暴露冻结快照并拒绝漂移。
"""
from examples.memory_inspect import run_inspect


def test_memory_inspect_runs_offline():
    """run_inspect returns a present Org snapshot, a Recruiter block, and a rejected drift.

    EN: org_snapshot contains the ORG MEMORY header; recruiter present; drift rejected.
    中文：org_snapshot 含 ORG MEMORY 头；recruiter 存在；漂移被拒。
    """
    out = run_inspect()
    assert out["org_snapshot"] and "ORG MEMORY" in out["org_snapshot"]
    assert out["recruiter_present"] is True
    assert out["drift_rejected"] is True
    assert len(out["org_entries"]) >= 1
