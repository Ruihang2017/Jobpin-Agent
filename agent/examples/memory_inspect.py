"""Offline inspect demo for the file-backed MemoryStore (§1.2).

EN —
Builds a store in a temp dir, adds a couple of Org standards and a Recruiter
preference, reloads to show the frozen system-prompt snapshot, then induces
external drift (an over-budget append) to show the next write is rejected with a
`.bak`. No key, no network. Returns a summary dict so it is assertable.

中文 —
在临时目录建一个存储，添加几条 Org 标准与一条 Recruiter 偏好，重载以展示冻结的系统提示快照，然后诱发外部漂移
（超预算追加）以展示下一次写入被拒并生成 `.bak`。无密钥、无网络。返回摘要字典以便断言。
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

# Allow `python agent/examples/memory_inspect.py` without setting PYTHONPATH.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpin_agent.memory.store import MemoryStore


def run_inspect() -> dict:
    """Run the inspect demo and return a summary dict.

    EN —
    Returns: ``{"org_entries", "org_snapshot", "recruiter_present", "drift_rejected"}``.
    中文 —
    返回：``{"org_entries", "org_snapshot", "recruiter_present", "drift_rejected"}``。
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="jobpin_mem_"))
    org_limit, recruiter_limit = 400, 200

    store = MemoryStore(tmp_dir, org_char_limit=org_limit, recruiter_char_limit=recruiter_limit)
    store.load_from_disk()
    store.add("org", "Score SWE candidates on demonstrated impact, not tenure.")
    store.add("org", "Always run a structured interview loop with a calibration step.")
    store.add("recruiter", "Prefers concise, evidence-cited candidate summaries.")

    # Reload to see the FROZEN snapshot (frozen at load time).
    reloaded = MemoryStore(tmp_dir, org_char_limit=org_limit, recruiter_char_limit=recruiter_limit)
    reloaded.load_from_disk()
    org_snapshot = reloaded.format_for_system_prompt("org")
    recruiter_present = reloaded.format_for_system_prompt("recruiter") is not None

    # Induce external drift: an over-budget single-entry append straight to the file.
    (tmp_dir / "ORG.md").write_text("X" * (org_limit + 500), encoding="utf-8")
    drift = reloaded.replace("org", "impact", "updated")

    return {
        "org_entries": reloaded._entries["org"],
        "org_snapshot": org_snapshot,
        "recruiter_present": recruiter_present,
        "drift_rejected": drift["success"] is False and "drift_backup" in drift,
    }


if __name__ == "__main__":  # pragma: no cover
    print(json.dumps(run_inspect(), ensure_ascii=False, indent=2))
