"""Offline demo for §1.3 — the memory backend wired to the §1.1 agent loop.

EN —
Builds a memory backend over a temp store (seeded with an Org standard + a fake
candidate-recall provider), runs ONE real §1.1 turn with a scripted FakeProvider
model, and shows three §1.3 outcomes without a key or network:
  1. the Org snapshot reaches the model's system prompt (the agent "knows" the bar),
  2. the seam's prefetch returns the fenced <memory-context> recall block,
  3. after the turn, sync is visible once flush_pending drains the worker.
Returns a summary dict so it is assertable.

中文 —
在临时存储上构建记忆后端（预置一条 Org 标准 + 一个 fake 候选召回 provider），用脚本化的 FakeProvider 模型运行
一个真实的 §1.1 回合，并在无密钥、无网络下展示三个 §1.3 结果：
  1. Org 快照到达模型的系统提示（agent “知道”用人标准），
  2. 接缝的 prefetch 返回围栏 <memory-context> 召回块，
  3. 回合后，待 flush_pending 排空工作线程，sync 可见。
返回摘要字典以便断言。
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

# Allow `python agent/examples/memory_agent_demo.py` without setting PYTHONPATH.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpin_agent.core.agent_loop import Agent
from jobpin_agent.core.messages import ModelResponse
from jobpin_agent.core.model.fake_provider import FakeProvider as FakeModel


class _RecallProvider:
    """A tiny fake provider that returns a fixed candidate recall (offline).

    EN — Stands in for a §1.4 entity provider; records syncs so the demo can show
    the turn persisted through the seam. 中文 — 替身 §1.4 实体 provider；记录 sync 以展示回合经接缝持久化。
    """

    def __init__(self, recall):
        """EN: Args: recall text. 中文：参数：召回文本。"""
        self._recall = recall
        self.synced = []

    @property
    def name(self):
        """EN: 'candidate-demo'. 中文：'candidate-demo'。"""
        return "candidate-demo"

    def is_available(self):
        """EN: True. 中文：True。"""
        return True

    def initialize(self, session_id, **kw):
        """EN: no-op. 中文：空操作。"""

    def system_prompt_block(self):
        """EN: no static block. 中文：无静态块。"""
        return ""

    def prefetch(self, query, *, session_id=""):
        """EN: the fixed recall. 中文：固定召回。"""
        return self._recall

    def queue_prefetch(self, query, *, session_id=""):
        """EN: no-op. 中文：空操作。"""

    def sync_turn(self, user, assistant, *, session_id="", messages=None):
        """EN: record the synced turn. 中文：记录已同步回合。"""
        self.synced.append((user, assistant))

    def get_tool_schemas(self):
        """EN: no tools. 中文：无工具。"""
        return []

    def on_pre_compress(self, messages):
        """EN: no facts. 中文：无事实。"""
        return ""

    def on_session_switch(self, new, *, parent_session_id="", reset=False, **kw):
        """EN: no-op. 中文：空操作。"""

    def on_delegation(self, task, result, *, child_session_id="", **kw):
        """EN: no-op. 中文：空操作。"""

    def shutdown(self):
        """EN: no-op. 中文：空操作。"""


def run_demo() -> dict:
    """Run the §1.3 demo and return a summary dict.

    EN —
    Returns: ``{"system_prompt_has_org", "prefetch_inner", "recall_in_prompt",
    "synced_after_turn", "answer"}``.
    中文 —
    返回：``{"system_prompt_has_org", "prefetch_inner", "recall_in_prompt",
    "synced_after_turn", "answer"}``。
    """
    # Imported here so the module import never fails if the optional stub is absent.
    from jobpin_agent.core.session_store import SessionStore
    from jobpin_agent.core.system_prompt import SystemPromptParts
    from jobpin_agent.core.tools import ToolRegistry
    from jobpin_agent.memory.composition import build_memory_backend

    tmp_dir = Path(tempfile.mkdtemp(prefix="jobpin_mem_agent_"))
    (tmp_dir / "ORG.md").write_text(
        "Score SWE candidates on demonstrated impact, not tenure.", encoding="utf-8"
    )
    recall = _RecallProvider("cand_7f3a: strong distributed-systems signal; prefers remote.")
    backend = build_memory_backend(tmp_dir, extra_providers=[recall])

    parts = SystemPromptParts(
        memory_snapshot=backend.memory_snapshot(),
        provider_block=backend.provider_block(),
    )
    store = SessionStore(":memory:")
    sid = store.create_session()
    model = FakeModel(script=[ModelResponse(text="Based on the bar, cand_7f3a looks strong.")])
    agent = Agent(model, ToolRegistry(), store, hooks=backend.hooks, parts=parts)

    prefetch_inner = backend.hooks.prefetch("who fits the SWE role?", sid)
    result = agent.run_turn(sid, "who fits the SWE role?")
    sent_blob = "\n".join(m.content for m in model.calls[0])
    backend.manager.flush_pending(2.0)

    return {
        "system_prompt_has_org": "demonstrated impact, not tenure" in sent_blob,
        "prefetch_inner": prefetch_inner,
        "recall_in_prompt": "<memory-context>" in sent_blob and "cand_7f3a" in sent_blob,
        "synced_after_turn": recall.synced == [("who fits the SWE role?", result.text)],
        "answer": result.text,
    }


if __name__ == "__main__":  # pragma: no cover
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print(json.dumps(run_demo(), ensure_ascii=False, indent=2))
