"""Tests for the governed ``memory`` write tool on ``BuiltinMemoryProvider`` (§1.5).

EN — An unlabelled write is rejected + audited; a fully-labelled write commits WITH the governance
header (100% labelled) + audits ``ok``; with no gate the provider keeps the §1.3 lean default (no tool).
中文 — 未标注写入被拒绝并审计；标注完整的写入携带治理头提交（100% 标注）并审计 ``ok``；无门控时保持 §1.3 精简默认
（无工具）。
"""
import json

from jobpin_agent.governance.audit import AuditLog
from jobpin_agent.governance.write_gate import GovernanceGate
from jobpin_agent.memory.providers.builtin import BuiltinMemoryProvider
from jobpin_agent.memory.store import load_org_recruiter_store


def _provider(tmp_path):
    """Build a builtin provider with a fresh gate + store under tmp_path.

    EN: Returns: (provider, gate). 中文：返回：(provider, gate)。
    """
    store = load_org_recruiter_store(str(tmp_path))
    gate = GovernanceGate(AuditLog())
    return BuiltinMemoryProvider(store, gate=gate, actor="recruiter:alice"), gate


def test_unlabelled_write_is_rejected(tmp_path):
    """A memory write with no provenance is rejected and recorded.

    EN: rejected:no_provenance. 中文：rejected:no_provenance。
    """
    provider, gate = _provider(tmp_path)
    out = json.loads(provider.handle_tool_call("memory", {"action": "add", "target": "org", "content": "x"}))
    assert out["success"] is False and out["rejected"] == "no_provenance"
    assert gate.audit.query()[-1].result == "rejected:no_provenance"


def test_labelled_write_commits_with_header(tmp_path):
    """A fully-labelled write commits, lands WITH the governance header, and audits ok.

    EN: header in the stored entry + write:add/ok. 中文：存储条目含治理头 + write:add/ok。
    """
    provider, gate = _provider(tmp_path)
    args = {"action": "add", "target": "org", "content": "weight reliability experience",
            "source_type": "recruiter_input", "source_ref": "rubric#1",
            "legal_basis": "legitimate_interest", "purpose": "hiring_calibration",
            "retention_policy": "not_hired_180d"}
    out = json.loads(provider.handle_tool_call("memory", args))
    assert out["success"] is True
    assert "key: acme:apac:org:policy" in "\n".join(provider.store._entries["org"])
    assert gate.audit.query(action="write:add")[-1].result == "ok"


def test_biased_write_is_blocked(tmp_path):
    """A write referencing a protected attribute is blocked by the gate (nothing stored).

    EN: rejected:bias + empty store. 中文：rejected:bias + 存储为空。
    """
    provider, gate = _provider(tmp_path)
    args = {"action": "add", "target": "org", "content": "Prefer candidates under 30 years old",
            "source_type": "recruiter_input", "source_ref": "rubric#2", "legal_basis": "legitimate_interest"}
    out = json.loads(provider.handle_tool_call("memory", args))
    assert out["success"] is False and out["code"] == "rejected:bias"
    assert provider.store._entries["org"] == []


def test_no_gate_keeps_lean_default(tmp_path):
    """Without a gate the provider exposes no tools (the §1.3 lean default is preserved).

    EN: get_tool_schemas() == []. 中文：get_tool_schemas() == []。
    """
    store = load_org_recruiter_store(str(tmp_path))
    provider = BuiltinMemoryProvider(store)
    assert provider.get_tool_schemas() == []
