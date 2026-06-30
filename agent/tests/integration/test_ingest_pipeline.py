"""Tests for the §1.10 ingest pipeline — the two exit criteria.

EN — exit 1: switch off, a read-only pull translates through the anti-corruption layer into the §1.8 local
store; exit 2 (dedicated): switch on ⇒ 0 outbound (the fetch is never called and nothing is ingested).

中文 — 退出 1：开关关闭时，只读拉取经反腐层翻译入 §1.8 本地库；退出 2（专项）：开关打开 ⇒ 0 出站（fetch 绝不被调用且
无入库）。
"""
import pytest

from jobpin_agent.data.store import CanonicalStore
from jobpin_agent.integration.connectors.fake_ats import FakeATSAntiCorruption, FakeATSConnector
from jobpin_agent.integration.outbound import OutboundBlocked, OutboundGuard
from jobpin_agent.integration.service import IntegrationService


def test_ingest_translates_into_local_store():
    """Exit 1: switch off → pull → translate → CanonicalStore has the canonical candidates. 中文 — 退出 1。"""
    store = CanonicalStore(db_path=":memory:")
    svc = IntegrationService(store, OutboundGuard(fully_local=False, audit=store.audit))
    res = svc.ingest(FakeATSConnector(), FakeATSAntiCorruption(), "candidate")
    assert res.count == 2
    got = store.get_candidate("A-1")
    assert got is not None and got.name == "Ada Lovelace" and "Python" in got.skills


def test_fully_local_zero_outbound():
    """Exit 2 (dedicated): default switch on → OutboundBlocked, fetch spy 0, nothing ingested. 中文 — 退出 2。"""
    store = CanonicalStore(db_path=":memory:")
    fetches = []

    class Spy(FakeATSConnector):
        def fetch(self, kind):
            fetches.append(kind)
            return super().fetch(kind)

    svc = IntegrationService(store, OutboundGuard(fully_local=True, audit=store.audit))
    with pytest.raises(OutboundBlocked):
        svc.ingest(Spy(), FakeATSAntiCorruption(), "candidate")
    assert fetches == []                       # the fetch never ran: 0 outbound
    assert store.get_candidate("A-1") is None  # nothing ingested


def test_unknown_kind_raises_before_any_egress():
    """An unknown kind raises ValueError BEFORE the fetch + writes no egress row. 中文 — 未知 kind 在出站前抛 ValueError 且无出站审计。"""
    store = CanonicalStore(db_path=":memory:")
    fetches = []

    class Spy(FakeATSConnector):
        def fetch(self, kind):
            fetches.append(kind)
            return super().fetch(kind)

    svc = IntegrationService(store, OutboundGuard(fully_local=False, audit=store.audit))
    with pytest.raises(ValueError):
        svc.ingest(Spy(), FakeATSAntiCorruption(), "spaceship")
    assert fetches == []                                    # validated before the (outbound) fetch
    assert store.audit.query(action="egress") == []         # no wasted egress audit row
