"""Tests for the §1.10 MCP tool-exposure skeleton — connector ops as registrable ToolSpecs.

EN — Proves connector_toolspecs yields ToolSpecs that register in a ToolRegistry and, when run (switch off),
ingest into the local store; a fully-local handler call returns a "blocked" string rather than raising.

中文 — 证明 connector_toolspecs 产出可注册进 ToolRegistry 的 ToolSpec，运行（开关关闭）时入本地库；完全本地的处理函数
调用返回“已阻断”字符串而非抛错。
"""
from jobpin_agent.core.tools import ToolRegistry
from jobpin_agent.data.store import CanonicalStore
from jobpin_agent.integration.connectors.fake_ats import FakeATSAntiCorruption, FakeATSConnector
from jobpin_agent.integration.mcp import connector_toolspecs, register_connector
from jobpin_agent.integration.outbound import OutboundGuard
from jobpin_agent.integration.service import IntegrationService


def test_toolspecs_registered_and_run():
    """ToolSpecs register and the handler ingests (switch off). 中文 — ToolSpec 注册且处理函数（开关关闭）入库。"""
    store = CanonicalStore(db_path=":memory:")
    svc = IntegrationService(store, OutboundGuard(fully_local=False, audit=store.audit))
    specs = connector_toolspecs(svc, FakeATSConnector(), FakeATSAntiCorruption(), ["candidate"])
    reg = ToolRegistry()
    register_connector(reg, *specs)
    assert reg.get("fake-ats_pull_candidate").name == "fake-ats_pull_candidate"
    out = specs[0].handler({})
    assert "2" in out and "candidate" in out
    assert store.get_candidate("A-1") is not None


def test_fully_local_handler_returns_blocked_string():
    """A fully-local handler call returns a blocked message, not an exception. 中文 — 完全本地处理函数返回阻断消息而非异常。"""
    store = CanonicalStore(db_path=":memory:")
    svc = IntegrationService(store, OutboundGuard(fully_local=True, audit=store.audit))
    specs = connector_toolspecs(svc, FakeATSConnector(), FakeATSAntiCorruption(), ["candidate"])
    out = specs[0].handler({})
    assert "blocked" in out.lower() and "fully-local" in out.lower()
    assert store.get_candidate("A-1") is None
