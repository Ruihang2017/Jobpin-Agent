"""Tests for the §1.10 OutboundGuard — fully-local blocks (0 outbound), switch-off runs + audits.

EN — Proves the default-on switch never invokes the wrapped call (0 outbound) and records the blocked
attempt; with the switch off the call runs once and an ``egress``/``ok`` audit row is written.

中文 — 证明默认开启的开关绝不调用被包裹的 call（0 出站）并记录被阻断的尝试；开关关闭时 call 运行一次且写入一行
``egress``/``ok`` 审计。
"""
import pytest

from jobpin_agent.data.store import CanonicalStore
from jobpin_agent.integration.outbound import OutboundBlocked, OutboundGuard


def test_fully_local_blocks_and_does_not_call():
    """Default switch on ⇒ OutboundBlocked + the call spy is never invoked. 中文 — 默认开启⇒阻断且 call 绝不被调用。"""
    calls = []
    g = OutboundGuard(fully_local=True)
    with pytest.raises(OutboundBlocked):
        g.send(target="fake-ats", fields=["candidate"], reason="pull:candidate", call=lambda: calls.append(1))
    assert calls == []


def test_switch_off_runs_and_audits():
    """Switch off ⇒ call runs once + an egress/ok audit row with the field set in the reason. 中文 — 关闭⇒运行 + egress/ok 审计。"""
    store = CanonicalStore(db_path=":memory:")
    g = OutboundGuard(fully_local=False, audit=store.audit, actor="alice")
    out = g.send(target="fake-ats", fields=["candidate"], reason="pull:candidate", call=lambda: 42)
    assert out == 42
    rows = store.audit.query(action="egress")
    assert len(rows) == 1
    assert rows[0].result == "ok" and rows[0].actor == "alice" and "fields=[candidate]" in rows[0].reason


def test_switch_off_failed_call_records_error_and_reraises():
    """A failing outbound call records egress/error (not ok) and propagates. 中文 — 失败的出站记 egress/error 并向上抛。"""
    store = CanonicalStore(db_path=":memory:")
    g = OutboundGuard(fully_local=False, audit=store.audit)

    def boom():
        raise RuntimeError("network down")

    with pytest.raises(RuntimeError):
        g.send(target="fake-ats", fields=["candidate"], reason="pull:candidate", call=boom)
    rows = store.audit.query(action="egress")
    assert len(rows) == 1 and rows[0].result == "error"


def test_fully_local_records_blocked_attempt():
    """A blocked attempt still leaves an egress/rejected:fully_local trace. 中文 — 被阻断的尝试仍留下 egress/rejected:fully_local 轨迹。"""
    store = CanonicalStore(db_path=":memory:")
    g = OutboundGuard(fully_local=True, audit=store.audit)
    with pytest.raises(OutboundBlocked):
        g.send(target="fake-ats", fields=["candidate"], reason="pull:candidate", call=lambda: 1)
    rows = store.audit.query(action="egress")
    assert len(rows) == 1 and rows[0].result == "rejected:fully_local"
