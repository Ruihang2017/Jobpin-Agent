"""File-backed curated memory store — ported from Hermes (MIT).

EN —
Ported from Hermes ``tools/memory_tool.py::MemoryStore`` (Nous Research, MIT). It
is the curated, low-volume, strongly-consistent layer of the Memory Subsystem
(PRD §9.3): a bounded, file-persisted store with two parallel states per target —
a FROZEN snapshot that enters the system prompt (stable for the whole session,
Key Invariant #1) and a LIVE entry list mutated by add/replace/remove and
persisted atomically to disk.

What changed vs Hermes (TEXTBOOK_SPEC Tenet 1): targets renamed memory→org and
user→recruiter (files ORG.md / RECRUITER.md); the injection scan is an injected
``scan_entry`` callable (the real ``threat_patterns`` library is ported at §1.6;
default is pass-through); char budgets recalibrated (Org raised, still bounded);
the governance header (provenance/consent/retention) is deferred to §1.5 — entries
stay opaque text. The core algorithms — dedup (``dict.fromkeys``), fixed-length
budget, atomic temp→fsync→``os.replace`` write under a ``.lock``, drift detection,
and ``apply_batch`` all-or-nothing — are ported unchanged.

中文 —
移植自 Hermes ``tools/memory_tool.py::MemoryStore``（Nous Research，MIT）。它是记忆子系统
（PRD §9.3）中经人工策展、低频、强一致的层：一个有界、文件持久化的存储，每个目标维护两个并行状态——进入系统
提示的**冻结快照**（整会话稳定，关键不变量 #1）与由 add/replace/remove 改动并原子落盘的**实时条目列表**。

相对 Hermes 的改动（TEXTBOOK_SPEC 第一原则）：目标重命名 memory→org、user→recruiter（文件 ORG.md /
RECRUITER.md）；注入扫描改为注入式 ``scan_entry`` 可调用对象（真实 ``threat_patterns`` 库在 §1.6 移植；默认放行）；
字符预算重新校准（Org 提高，仍有界）；治理头（来源/同意/留存）推迟到 §1.5——条目保持为不透明文本。核心算法——
去重（``dict.fromkeys``）、定长预算、原子写（temp→fsync→``os.replace``）+ ``.lock``、漂移检测、
``apply_batch`` 全有或全无——原样移植。
"""
from __future__ import annotations

import logging
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
    import fcntl
    msvcrt = None
except ImportError:  # pragma: no cover - Windows path
    fcntl = None
    try:
        import msvcrt
    except ImportError:  # pragma: no cover
        msvcrt = None

logger = logging.getLogger(__name__)

ENTRY_DELIMITER = "\n§\n"

# Threat-scan seam: returns a short description if the entry is dangerous, else None.
# The real threat_patterns-based scanner is injected at §1.6; default is pass-through.
ScanEntry = Callable[[str], Optional[str]]
# Optional approval/staging hook: (action, target, content) -> held message or None.
WriteGate = Callable[[str, str, Optional[str]], Optional[str]]

_FILENAMES: Dict[str, str] = {"org": "ORG.md", "recruiter": "RECRUITER.md"}


def _no_scan(_text: str) -> Optional[str]:
    """Default threat scan: never blocks (real patterns arrive at §1.6).

    EN: Args: _text (ignored). Returns: None (treated as clean).
    中文：参数：_text（忽略）。返回：None（视为干净）。
    """
    return None


def _drift_error(path: Path, bak_path: str) -> Dict[str, Any]:
    """Build the error dict returned when external drift is detected (ported).

    EN —
    The on-disk file holds content that wouldn't round-trip through the
    parser/serialiser; rewriting would discard it, so we refuse the write and
    point at the ``.bak`` snapshot.
    Args: path — the memory file; bak_path — the snapshot path taken.
    Returns: an error dict (``success=False`` + ``drift_backup`` + ``remediation``).

    中文 —
    磁盘文件含无法往返解析/序列化的内容；重写会丢弃它，故拒绝写入并指向 ``.bak`` 快照。
    参数：path——记忆文件；bak_path——所取快照路径。返回：错误字典（``success=False`` + ``drift_backup`` + ``remediation``）。
    """
    return {
        "success": False,
        "error": (
            f"Refusing to write {path.name}: the file on disk has content that "
            f"wouldn't round-trip through the memory tool (likely a manual edit, a "
            f"shell append, or a concurrent session). A snapshot was saved to "
            f"{bak_path}. Resolve the drift first, then retry. This guard prevents "
            f"silent data loss."
        ),
        "drift_backup": bak_path,
        "remediation": (
            "Open the .bak file, re-add the missing entries one at a time, then "
            "rewrite the original file to a clean §-delimited list."
        ),
    }


class MemoryStore:
    """Bounded curated memory with file persistence (targets: org, recruiter).

    EN —
    Ported from Hermes ``tools/memory_tool.py::MemoryStore`` (MIT). Two parallel
    states per target: a FROZEN snapshot (enters the system prompt, set once at
    ``load_from_disk()``, never mutated mid-session — keeps the prefix cache stable)
    and a LIVE entry list (mutated by add/replace/remove, persisted atomically).
    ``target ∈ {"org","recruiter"}``. The injection scan is injected (``scan_entry``);
    the governance header and the real threat patterns arrive at §1.5 / §1.6.

    中文 —
    移植自 Hermes ``tools/memory_tool.py::MemoryStore``（MIT）。每个目标维护两个并行状态：**冻结快照**
    （进入系统提示，在 ``load_from_disk()`` 时设定一次、会话中不变——保持前缀缓存稳定）与**实时条目列表**
    （由 add/replace/remove 改动，原子落盘）。``target ∈ {"org","recruiter"}``。注入扫描为注入式
    （``scan_entry``）；治理头与真实威胁模式在 §1.5 / §1.6 引入。
    """

    def __init__(
        self,
        memory_dir,
        org_char_limit: int = 6000,
        recruiter_char_limit: int = 2000,
        scan_entry: Optional[ScanEntry] = None,
        write_gate: Optional[WriteGate] = None,
    ) -> None:
        """Construct a store rooted at ``memory_dir``.

        EN —
        Args:
            memory_dir: directory holding ORG.md / RECRUITER.md.
            org_char_limit / recruiter_char_limit: bounded char budgets (high-SNR).
            scan_entry: threat scan returning a description or ``None`` (default pass-through).
            write_gate: optional approval hook (default pass-through).
        Call ``load_from_disk()`` before reading the snapshot.

        中文 —
        参数：
            memory_dir：存放 ORG.md / RECRUITER.md 的目录。
            org_char_limit / recruiter_char_limit：有界字符预算（高信噪比）。
            scan_entry：返回威胁描述或 ``None`` 的扫描（默认放行）。
            write_gate：可选审批钩子（默认放行）。
        读取快照前先调用 ``load_from_disk()``。
        """
        self._memory_dir = Path(memory_dir)
        self._limits: Dict[str, int] = {"org": org_char_limit, "recruiter": recruiter_char_limit}
        self._entries: Dict[str, List[str]] = {"org": [], "recruiter": []}
        self._snapshot: Dict[str, str] = {"org": "", "recruiter": ""}
        self._scan: ScanEntry = scan_entry or _no_scan
        self._write_gate = write_gate

    def load_from_disk(self) -> None:
        """Load entries from disk and freeze the system-prompt snapshot (ported).

        EN —
        For each target: read the file → split on ``ENTRY_DELIMITER`` → drop blanks →
        deduplicate (``dict.fromkeys``, order-preserving) → scan each entry (a hit is
        replaced by ``[BLOCKED:]`` in the snapshot while the live list keeps the
        original) → freeze the snapshot. Deterministic from disk bytes, so the
        snapshot is stable for the whole session (Key Invariant #1).

        中文 —
        对每个目标：读取文件 → 按 ``ENTRY_DELIMITER`` 切分 → 去空 → 去重（``dict.fromkeys``，保序）→
        扫描每条（命中则在快照中以 ``[BLOCKED:]`` 替换，实时列表保留原文）→ 冻结快照。由磁盘字节确定，故快照整会话稳定
        （关键不变量 #1）。
        """
        self._memory_dir.mkdir(parents=True, exist_ok=True)
        for target in ("org", "recruiter"):
            entries = list(dict.fromkeys(self._read_file(self._path_for(target))))
            self._entries[target] = entries
            sanitized = self._sanitize_entries_for_snapshot(entries, _FILENAMES[target])
            self._snapshot[target] = self._render_block(target, sanitized)

    def _sanitize_entries_for_snapshot(self, entries: List[str], filename: str) -> List[str]:
        """Replace threat-matching entries with a ``[BLOCKED:]`` placeholder (ported).

        EN —
        Scans each entry with the injected ``scan_entry``. On a hit the entry is
        replaced (in the returned list, used only for the snapshot) with a
        ``[BLOCKED: <file> entry contained threat pattern(s): <desc>. …]`` marker;
        the live state keeps the original for the user to inspect and remove. Empty
        or already-blocked entries pass through.
        Args: entries — live entries; filename — for the marker text.
        Returns: the sanitised list for the snapshot.

        中文 —
        用注入的 ``scan_entry`` 扫描每条。命中则在返回列表（仅用于快照）中以
        ``[BLOCKED: <文件> entry contained threat pattern(s): <desc>. …]`` 标记替换；实时状态保留原文供用户查看与删除。
        空或已屏蔽的条目原样通过。
        参数：entries——实时条目；filename——用于标记文本。返回：用于快照的净化列表。
        """
        sanitized: List[str] = []
        for entry in entries:
            if not entry or entry.startswith("[BLOCKED:"):
                sanitized.append(entry)
                continue
            desc = self._scan(entry)
            if desc:
                logger.warning("Memory entry from %s blocked at load time: %s", filename, desc)
                sanitized.append(
                    f"[BLOCKED: {filename} entry contained threat pattern(s): {desc}. "
                    f"Removed from system prompt; use remove() to delete the original.]"
                )
            else:
                sanitized.append(entry)
        return sanitized

    @staticmethod
    @contextmanager
    def _file_lock(path: Path):
        """Exclusive lock via a separate ``.lock`` file (fcntl / msvcrt) (ported).

        EN —
        Locking a separate ``.lock`` file lets the memory file itself still be
        atomically replaced via ``os.replace``. No-op if neither lock API exists.
        Args: path — the memory file (the lock is ``path.lock``).

        中文 —
        锁一个独立的 ``.lock`` 文件，使记忆文件本身仍可经 ``os.replace`` 原子替换。两种锁 API 都不存在时为空操作。
        参数：path——记忆文件（锁为 ``path.lock``）。
        """
        lock_path = path.with_suffix(path.suffix + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        if fcntl is None and msvcrt is None:
            yield
            return
        fd = open(lock_path, "a+", encoding="utf-8")
        try:
            if fcntl:
                fcntl.flock(fd, fcntl.LOCK_EX)
            else:
                fd.seek(0)
                msvcrt.locking(fd.fileno(), msvcrt.LK_LOCK, 1)
            yield
        finally:
            if fcntl:
                try:
                    fcntl.flock(fd, fcntl.LOCK_UN)
                except (OSError, IOError):
                    pass
            elif msvcrt:
                try:
                    fd.seek(0)
                    msvcrt.locking(fd.fileno(), msvcrt.LK_UNLCK, 1)
                except (OSError, IOError):
                    pass
            fd.close()

    def _path_for(self, target: str) -> Path:
        """Return the file path for a target. (ported; uses the injected dir)

        EN: Args: target. Returns: ``memory_dir / ORG.md`` or ``RECRUITER.md``.
        中文：参数：target。返回：``memory_dir / ORG.md`` 或 ``RECRUITER.md``。
        """
        return self._memory_dir / _FILENAMES[target]

    def _reload_target(self, target: str, *, skip_drift: bool = False) -> Optional[str]:
        """Re-read entries under lock; return a ``.bak`` path if drift detected (ported).

        EN —
        Args: target; skip_drift — bypass the round-trip/size check (used by append-only
        ``add`` which never clobbers existing content).
        Returns: the backup path if external drift was detected (caller must abort), else None.

        中文 —
        参数：target；skip_drift——跳过往返/大小检查（供仅追加的 ``add`` 使用，它不会覆盖既有内容）。
        返回：检测到外部漂移时返回备份路径（调用方须中止），否则 None。
        """
        bak = None if skip_drift else self._detect_external_drift(target)
        fresh = list(dict.fromkeys(self._read_file(self._path_for(target))))
        self._entries[target] = fresh
        return bak

    def save_to_disk(self, target: str) -> None:
        """Persist a target's live entries atomically. (ported)

        EN: Args: target. Writes via temp→fsync→os.replace.
        中文：参数：target。经 temp→fsync→os.replace 写入。
        """
        self._memory_dir.mkdir(parents=True, exist_ok=True)
        self._write_file(self._path_for(target), self._entries[target])

    def _char_count(self, target: str) -> int:
        """Current char count of a target (delimiter-joined). (ported)

        EN: Args: target. Returns: char length, 0 if empty.
        中文：参数：target。返回：字符长度，空则 0。
        """
        entries = self._entries[target]
        return len(ENTRY_DELIMITER.join(entries)) if entries else 0

    def _char_limit(self, target: str) -> int:
        """The char budget for a target. (ported)

        EN: Args: target. Returns: the configured limit.
        中文：参数：target。返回：配置的上限。
        """
        return self._limits[target]

    def _gate(self, action: str, target: str, content: Optional[str]) -> Optional[str]:
        """Apply the optional write gate. (new — §1.2 seam)

        EN: Args: action, target, content. Returns: a held message (write refused) or None.
        中文：参数：action、target、content。返回：保留消息（拒绝写入）或 None。
        """
        if self._write_gate is None:
            return None
        return self._write_gate(action, target, content)

    def add(self, target: str, content: str) -> Dict[str, Any]:
        """Append a new entry (scan → gate → budget). (ported + injected scan/gate)

        EN —
        Args: target; content. Returns: a success dict, or an error dict (empty,
        scan-blocked, staged by the gate, duplicate-skip, or over-budget with
        ``current_entries``).

        中文 —
        参数：target；content。返回：成功字典，或错误字典（为空、被扫描拦截、被门控暂存、重复跳过，或超预算并附
        ``current_entries``）。
        """
        content = content.strip()
        if not content:
            return {"success": False, "error": "Content cannot be empty."}
        desc = self._scan(content)
        if desc:
            return {"success": False, "error": f"Entry blocked by scan: {desc}"}
        held = self._gate("add", target, content)
        if held:
            return {"success": False, "staged": True, "message": held}
        with self._file_lock(self._path_for(target)):
            self._reload_target(target, skip_drift=True)
            entries = self._entries[target]
            limit = self._char_limit(target)
            if content in entries:
                return self._success_response(target, "Entry already exists (no duplicate added).")
            new_total = len(ENTRY_DELIMITER.join(entries + [content]))
            if new_total > limit:
                current = self._char_count(target)
                return {
                    "success": False,
                    "error": (
                        f"Memory at {current:,}/{limit:,} chars. Adding this entry "
                        f"({len(content)} chars) would exceed the limit. Consolidate "
                        f"(replace/remove) then retry — all in this turn."
                    ),
                    "current_entries": list(entries),
                    "usage": f"{current:,}/{limit:,}",
                }
            entries.append(content)
            self.save_to_disk(target)
        return self._success_response(target, "Entry added.")

    def replace(self, target: str, old_text: str, new_content: str) -> Dict[str, Any]:
        """Replace the entry containing ``old_text`` (unique-substring). (ported + scan/gate)

        EN —
        Args: target; old_text (substring); new_content. Returns: success, or an error
        dict (empty, scan-blocked, staged, drift, no-match, ambiguous ``matches``, or
        over-budget).

        中文 —
        参数：target；old_text（子串）；new_content。返回：成功，或错误字典（为空、被扫描拦截、暂存、漂移、无匹配、
        歧义 ``matches``，或超预算）。
        """
        old_text = old_text.strip()
        new_content = new_content.strip()
        if not old_text:
            return {"success": False, "error": "old_text cannot be empty."}
        if not new_content:
            return {"success": False, "error": "new_content cannot be empty. Use remove() to delete entries."}
        desc = self._scan(new_content)
        if desc:
            return {"success": False, "error": f"Entry blocked by scan: {desc}"}
        held = self._gate("replace", target, new_content)
        if held:
            return {"success": False, "staged": True, "message": held}
        with self._file_lock(self._path_for(target)):
            bak = self._reload_target(target)
            if bak:
                return _drift_error(self._path_for(target), bak)
            entries = self._entries[target]
            matches = [(i, e) for i, e in enumerate(entries) if old_text in e]
            if not matches:
                return {"success": False, "error": f"No entry matched '{old_text}'."}
            if len(matches) > 1 and len({e for _, e in matches}) > 1:
                previews = [e[:80] + ("..." if len(e) > 80 else "") for _, e in matches]
                return {
                    "success": False,
                    "error": f"Multiple entries matched '{old_text}'. Be more specific.",
                    "matches": previews,
                }
            idx = matches[0][0]
            limit = self._char_limit(target)
            test_entries = entries.copy()
            test_entries[idx] = new_content
            new_total = len(ENTRY_DELIMITER.join(test_entries))
            if new_total > limit:
                current = self._char_count(target)
                return {
                    "success": False,
                    "error": (
                        f"Replacement would put memory at {new_total:,}/{limit:,} chars. "
                        f"Shorten the new content, or remove other entries to make room, then retry."
                    ),
                    "current_entries": list(entries),
                    "usage": f"{current:,}/{limit:,}",
                }
            entries[idx] = new_content
            self.save_to_disk(target)
        return self._success_response(target, "Entry replaced.")

    def remove(self, target: str, old_text: str) -> Dict[str, Any]:
        """Remove the entry containing ``old_text`` (unique-substring). (ported + gate)

        EN —
        Args: target; old_text (substring). Returns: success, or an error dict (empty,
        staged, drift, no-match, ambiguous ``matches``).

        中文 —
        参数：target；old_text（子串）。返回：成功，或错误字典（为空、暂存、漂移、无匹配、歧义 ``matches``）。
        """
        old_text = old_text.strip()
        if not old_text:
            return {"success": False, "error": "old_text cannot be empty."}
        held = self._gate("remove", target, None)
        if held:
            return {"success": False, "staged": True, "message": held}
        with self._file_lock(self._path_for(target)):
            bak = self._reload_target(target)
            if bak:
                return _drift_error(self._path_for(target), bak)
            entries = self._entries[target]
            matches = [(i, e) for i, e in enumerate(entries) if old_text in e]
            if not matches:
                return {"success": False, "error": f"No entry matched '{old_text}'."}
            if len(matches) > 1 and len({e for _, e in matches}) > 1:
                previews = [e[:80] + ("..." if len(e) > 80 else "") for _, e in matches]
                return {
                    "success": False,
                    "error": f"Multiple entries matched '{old_text}'. Be more specific.",
                    "matches": previews,
                }
            entries.pop(matches[0][0])
            self.save_to_disk(target)
        return self._success_response(target, "Entry removed.")

    def apply_batch(self, target: str, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply add/replace/remove ops atomically against the FINAL budget. (ported + scan/gate)

        EN —
        All-or-nothing: validate every op on a working copy; intermediate overflow is
        allowed, only the final char count is budget-checked; commit only if all pass.
        Args: target; operations — list of ``{"action", "content"?, "old_text"?}``.
        Returns: success, or an error dict (scan-blocked, staged, drift, malformed/no-match/
        ambiguous op, or final over-budget) with nothing written.

        中文 —
        全有或全无：在工作副本上校验每个操作；允许中间超额，仅对最终字符数做预算检查；全部通过才提交。
        参数：target；operations——``{"action", "content"?, "old_text"?}`` 列表。
        返回：成功，或错误字典（被扫描拦截、暂存、漂移、操作畸形/无匹配/歧义，或最终超预算），且不写入任何内容。
        """
        if not operations:
            return {"success": False, "error": "operations list is empty."}
        for i, op in enumerate(operations):
            act = (op or {}).get("action")
            new_content = (op or {}).get("content")
            if act in {"add", "replace"} and new_content:
                desc = self._scan(new_content)
                if desc:
                    return {"success": False, "error": f"Operation {i + 1}: blocked by scan: {desc}"}
        held = self._gate("apply_batch", target, None)
        if held:
            return {"success": False, "staged": True, "message": held}
        with self._file_lock(self._path_for(target)):
            bak = self._reload_target(target)
            if bak:
                return _drift_error(self._path_for(target), bak)
            working: List[str] = list(self._entries[target])
            limit = self._char_limit(target)
            for i, op in enumerate(operations):
                op = op or {}
                act = op.get("action")
                content = (op.get("content") or "").strip()
                old_text = (op.get("old_text") or "").strip()
                pos = f"Operation {i + 1} ({act or 'unknown'})"
                if act == "add":
                    if not content:
                        return self._batch_error(target, f"{pos}: content is required.")
                    if content in working:
                        continue  # idempotent — skip duplicate, don't fail the batch
                    working.append(content)
                elif act == "replace":
                    if not old_text:
                        return self._batch_error(target, f"{pos}: old_text is required.")
                    if not content:
                        return self._batch_error(target, f"{pos}: content is required (use remove to delete).")
                    matches = [j for j, e in enumerate(working) if old_text in e]
                    if not matches:
                        return self._batch_error(target, f"{pos}: no entry matched '{old_text}'.")
                    if len({working[j] for j in matches}) > 1:
                        return self._batch_error(target, f"{pos}: '{old_text}' matched multiple distinct entries — be more specific.")
                    working[matches[0]] = content
                elif act == "remove":
                    if not old_text:
                        return self._batch_error(target, f"{pos}: old_text is required.")
                    matches = [j for j, e in enumerate(working) if old_text in e]
                    if not matches:
                        return self._batch_error(target, f"{pos}: no entry matched '{old_text}'.")
                    if len({working[j] for j in matches}) > 1:
                        return self._batch_error(target, f"{pos}: '{old_text}' matched multiple distinct entries — be more specific.")
                    working.pop(matches[0])
                else:
                    return self._batch_error(target, f"{pos}: unknown action. Use add, replace, or remove.")
            new_total = len(ENTRY_DELIMITER.join(working)) if working else 0
            if new_total > limit:
                current = self._char_count(target)
                return {
                    "success": False,
                    "error": (
                        f"After applying all {len(operations)} operations, memory would be at "
                        f"{new_total:,}/{limit:,} chars — over the limit. Remove or shorten more "
                        f"entries in the same batch, then retry."
                    ),
                    "current_entries": list(self._entries[target]),
                    "usage": f"{current:,}/{limit:,}",
                }
            self._entries[target] = working
            self.save_to_disk(target)
        return self._success_response(target, f"Applied {len(operations)} operation(s).")

    def _batch_error(self, target: str, message: str) -> Dict[str, Any]:
        """Build a batch-abort error reporting live (uncommitted) state. (ported)

        EN: Args: target; message. Returns: an all-or-nothing error dict with ``current_entries``.
        中文：参数：target；message。返回：含 ``current_entries`` 的全有或全无错误字典。
        """
        current = self._char_count(target)
        limit = self._char_limit(target)
        return {
            "success": False,
            "error": message + " No operations were applied (batch is all-or-nothing).",
            "current_entries": list(self._entries[target]),
            "usage": f"{current:,}/{limit:,}",
        }

    def format_for_system_prompt(self, target: str) -> Optional[str]:
        """Return the FROZEN snapshot block for the system prompt. (ported)

        EN —
        Returns the state captured at ``load_from_disk()``, NOT the live state, so the
        system prompt stays stable across turns (prefix cache). Returns ``None`` if empty.
        Args: target. Returns: the snapshot block, or None.

        中文 —
        返回 ``load_from_disk()`` 时捕获的状态，而非实时状态，使系统提示跨回合稳定（前缀缓存）。空则返回 ``None``。
        参数：target。返回：快照块或 None。
        """
        block = self._snapshot.get(target, "")
        return block if block else None

    def _success_response(self, target: str, message: Optional[str] = None) -> Dict[str, Any]:
        """Build the lean (terminal) success response. (ported — anti-churn)

        EN —
        Deliberately does NOT echo the full entries list (echoing invites the model to
        "find more to fix" and re-issue ops). Entries are shown only on error paths.
        Args: target; message. Returns: a success dict (usage %, entry_count, note).

        中文 —
        刻意不回显完整条目列表（回显会诱使模型“再找点改”并重复操作）。条目仅在错误路径展示。
        参数：target；message。返回：成功字典（用量百分比、entry_count、note）。
        """
        entries = self._entries[target]
        current = self._char_count(target)
        limit = self._char_limit(target)
        pct = min(100, int((current / limit) * 100)) if limit > 0 else 0
        resp: Dict[str, Any] = {
            "success": True,
            "done": True,
            "target": target,
            "usage": f"{pct}% — {current:,}/{limit:,} chars",
            "entry_count": len(entries),
        }
        if message:
            resp["message"] = message
        resp["note"] = "Write saved. This update is complete — do not repeat it."
        return resp

    def _render_block(self, target: str, entries: List[str]) -> str:
        """Render a system-prompt block with header + usage. (ported; HR labels)

        EN: Args: target; entries. Returns: the rendered block, or "" if empty.
        中文：参数：target；entries。返回：渲染后的块，空则返回 ""。
        """
        if not entries:
            return ""
        limit = self._char_limit(target)
        content = ENTRY_DELIMITER.join(entries)
        current = len(content)
        pct = min(100, int((current / limit) * 100)) if limit > 0 else 0
        if target == "recruiter":
            header = f"RECRUITER PROFILE (preferences, the hiring bar) [{pct}% — {current:,}/{limit:,} chars]"
        else:
            header = f"ORG MEMORY (hiring standards, rubrics, policy) [{pct}% — {current:,}/{limit:,} chars]"
        separator = "═" * 46
        return f"{separator}\n{header}\n{separator}\n{content}"

    @staticmethod
    def _read_file(path: Path) -> List[str]:
        """Read a memory file and split into entries. (ported)

        EN —
        No lock needed: ``_write_file`` uses atomic rename, so readers always see a
        complete file. Splits on ``ENTRY_DELIMITER`` (not bare "§").
        Args: path. Returns: the non-empty stripped entries (``[]`` if absent/empty).

        中文 —
        无需加锁：``_write_file`` 用原子重命名，故读者总能看到完整文件。按 ``ENTRY_DELIMITER``（而非裸 "§"）切分。
        参数：path。返回：非空、去空白的条目（缺失/为空则 ``[]``）。
        """
        if not path.exists():
            return []
        try:
            raw = path.read_text(encoding="utf-8")
        except (OSError, IOError):
            return []
        if not raw.strip():
            return []
        entries = [e.strip() for e in raw.split(ENTRY_DELIMITER)]
        return [e for e in entries if e]

    def _detect_external_drift(self, target: str) -> Optional[str]:
        """Return a ``.bak`` path if on-disk content shows external drift. (ported)

        EN —
        Two signals: (1) round-trip mismatch (re-parse+re-serialise ≠ original bytes);
        (2) any single parsed entry exceeds the whole-store char limit (an external
        writer appended free-form content). On drift, snapshot to ``path.bak.<ts>`` and
        return that path so the caller refuses the write.
        Args: target. Returns: the ``.bak`` path on drift, else None.

        中文 —
        两个信号：(1) 往返不一致（重解析+重序列化 ≠ 原始字节）；(2) 任一解析条目超过整库字符上限（外部写入追加了自由内容）。
        漂移时快照到 ``path.bak.<ts>`` 并返回该路径，使调用方拒绝写入。
        参数：target。返回：漂移时返回 ``.bak`` 路径，否则 None。
        """
        path = self._path_for(target)
        if not path.exists():
            return None
        try:
            raw = path.read_text(encoding="utf-8")
        except (OSError, IOError):
            return None
        if not raw.strip():
            return None
        parsed = [e.strip() for e in raw.split(ENTRY_DELIMITER) if e.strip()]
        roundtrip = ENTRY_DELIMITER.join(parsed)
        limit = self._char_limit(target)
        max_entry_len = max((len(e) for e in parsed), default=0)
        if (raw.strip() != roundtrip) or (max_entry_len > limit):
            ts = int(time.time())
            bak_path = path.with_suffix(path.suffix + f".bak.{ts}")
            try:
                bak_path.write_text(raw, encoding="utf-8")
            except (OSError, IOError):
                return str(bak_path) + " (BACKUP FAILED — file unchanged on disk)"
            return str(bak_path)
        return None

    @staticmethod
    def _write_file(path: Path, entries: List[str]) -> None:
        """Write entries atomically (temp → fsync → ``os.replace``). (ported)

        EN —
        Atomic rename means concurrent readers always see the old or new complete file,
        never a truncated one. Cleans up the temp file on any failure.
        Args: path; entries.

        中文 —
        原子重命名意味着并发读者总能看到旧或新的完整文件，绝不见截断文件。任何失败都清理临时文件。
        参数：path；entries。
        """
        content = ENTRY_DELIMITER.join(entries) if entries else ""
        try:
            fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp", prefix=".mem_")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_path, path)
            except BaseException:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except (OSError, IOError) as e:
            raise RuntimeError(f"Failed to write memory file {path}: {e}")


def load_org_recruiter_store(
    memory_dir,
    scan_entry: Optional[ScanEntry] = None,
    write_gate: Optional[WriteGate] = None,
) -> MemoryStore:
    """Build a :class:`MemoryStore` and load it from disk. (factory)

    EN —
    Args: memory_dir; scan_entry (default pass-through); write_gate (default pass-through).
    Returns: a loaded store ready for ``format_for_system_prompt`` / add / replace / remove.

    中文 —
    参数：memory_dir；scan_entry（默认放行）；write_gate（默认放行）。
    返回：已加载、可用于 ``format_for_system_prompt`` / add / replace / remove 的存储。
    """
    store = MemoryStore(memory_dir, scan_entry=scan_entry, write_gate=write_gate)
    store.load_from_disk()
    return store
