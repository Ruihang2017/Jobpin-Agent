"""End-to-end §1.5 composition — governed write through the loop + RBAC recall isolation.

EN —
Two integration proofs that the layers compose with NO change to ``agent_loop.py``:
1. RBAC recall isolation — a principal scoped to one org recalls only that org's candidates; an
   out-of-scope candidate's very existence never leaks (filter-before-NN, exit criterion 3).
2. The governed ``memory`` tool, reached only through the existing ``ToolRegistry`` via the
   registry→manager bridge, commits a fully-labelled write inside a real ``Agent.run_turn`` and audits
   it — the loop is untouched.

中文 —
两个集成证明，表明各层在**不改动 ``agent_loop.py``** 的前提下组合：
1. RBAC 召回隔离——限定到某组织的 principal 仅召回该组织候选人；范围外候选人的存在性绝不泄漏（先过滤再近邻，
   退出标准 3）。
2. 受治理的 ``memory`` 工具仅经既有 ``ToolRegistry`` 通过注册表→manager 桥到达，在真实 ``Agent.run_turn`` 内提交
   标注完整的写入并审计——循环未动。
"""
from jobpin_agent.core.agent_loop import Agent
from jobpin_agent.core.messages import ModelResponse, ToolCall
from jobpin_agent.core.model.fake_provider import FakeProvider
from jobpin_agent.core.session_store import SessionStore
from jobpin_agent.core.tools import ToolRegistry
from jobpin_agent.governance.audit import AuditLog
from jobpin_agent.governance.rbac import Principal, scope_predicate
from jobpin_agent.governance.tool_bridge import build_memory_tool
from jobpin_agent.governance.write_gate import GovernanceGate
from jobpin_agent.memory.embedding import hashing_embedder
from jobpin_agent.memory.manager import MemoryManager
from jobpin_agent.memory.manager_hooks import MemoryManagerHooks
from jobpin_agent.memory.providers.builtin import BuiltinMemoryProvider
from jobpin_agent.memory.providers.candidate import CandidateMemoryProvider
from jobpin_agent.memory.store import load_org_recruiter_store
from jobpin_agent.memory.structured import CandidateRow, CandidateStructuredStore
from jobpin_agent.memory.vector.store import SqliteVectorStore


def test_rbac_recall_isolation():
    """A principal scoped to acme:apac recalls only the apac candidate; the emea one never leaks.

    EN: exit criterion 3 (filter-before-NN). 中文：退出标准 3（先过滤再近邻）。
    """
    provider = CandidateMemoryProvider(
        SqliteVectorStore(), CandidateStructuredStore(), hashing_embedder(256), embed_version="hash@256",
        scope_filter=scope_predicate(Principal("alice", "recruiter", ("acme:apac",))))
    provider.ingest(CandidateRow("acme:apac:candidate:a", name="A"),
                    [("acme:apac:candidate:a#0", "python postgres reliability")])
    provider.ingest(CandidateRow("acme:emea:candidate:b", name="B"),
                    [("acme:emea:candidate:b#0", "python postgres reliability")])
    recall = provider.prefetch("python postgres reliability", session_id="s")
    assert "acme:apac:candidate:a" in recall
    assert "acme:emea:candidate:b" not in recall   # B's existence never leaks


def test_governed_tool_through_loop(tmp_path):
    """A fully-labelled memory tool call inside Agent.run_turn commits + audits (no loop change).

    EN: governed write end-to-end via the ToolRegistry bridge. 中文：经 ToolRegistry 桥端到端受治理写入。
    """
    store = load_org_recruiter_store(str(tmp_path))
    gate = GovernanceGate(AuditLog())
    manager = MemoryManager()
    manager.add_provider(BuiltinMemoryProvider(store, gate=gate, actor="recruiter:alice"))

    tools = ToolRegistry()
    tools.register(build_memory_tool(manager))

    model = FakeProvider(script=[
        ModelResponse(tool_calls=[ToolCall(id="1", name="memory", arguments={
            "action": "add", "target": "org", "content": "weight distributed-systems experience",
            "source_type": "recruiter_input", "source_ref": "rubric#1",
            "legal_basis": "legitimate_interest", "retention_policy": "not_hired_180d"})]),
        ModelResponse(text="done — recorded as a suggestion for human review"),
    ])
    sessions = SessionStore(":memory:")
    sid = sessions.create_session()
    agent = Agent(model, tools, sessions, hooks=MemoryManagerHooks(manager))

    result = agent.run_turn(sid, "remember: weight distributed-systems experience")
    assert result.text and not result.stopped
    assert "key: acme:apac:org:policy" in "\n".join(store._entries["org"])
    assert gate.audit.query(action="write:add")[-1].result == "ok"
