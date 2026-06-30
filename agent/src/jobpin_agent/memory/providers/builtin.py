"""The built-in memory provider — wraps the §1.2 file-backed ``MemoryStore``.

EN —
Makes the curated Org/Recruiter store (§1.2) participate in the ``MemoryProvider``
lifecycle so the Manager can orchestrate it alongside future entity providers
(§1.4), and so file-backed memory gets the ``on_pre_compress`` seam the §1.6
pre-compression wiring needs ("MemoryStore is not a Provider" gap, Plan §1.6).

§1.3 kept it deliberately lean (read/seam path only); §1.5 lights up the write tool:
- The curated frozen snapshot reaches the system prompt DIRECTLY via the §1.1
  ``memory_snapshot`` slot (assembly order, Plan §1.1), so ``system_prompt_block``
  returns ``""`` here — returning the snapshot would duplicate it.
- ``prefetch`` returns ``""`` (curated memory is static in the prompt; per-query
  recall is §1.4's vector providers).
- ``sync_turn`` is a no-op (curated memory is not auto-written per turn; writes go
  through the model-facing governed ``memory`` tool below, not background sync).
- ``get_tool_schemas`` returns the governed ``memory`` write tool **when a §1.5
  ``GovernanceGate`` is injected** (``gate=``); without a gate it returns ``[]``
  (the §1.3 lean default, preserved for back-compat). ``handle_tool_call`` runs the
  gate as a pre-check (reject unlabelled / unconsented / biased writes), prefixes
  the validated governance header onto the entry, then calls the §1.2 store — so the
  ported ``MemoryStore`` is unchanged and 100% of accepted writes carry labels.

中文 —
让策展的 Org/Recruiter 存储（§1.2）参与 ``MemoryProvider`` 生命周期，使 Manager 能与未来的实体 provider
（§1.4）一同编排它，并让文件型记忆获得 §1.6 压缩前接线所需的 ``on_pre_compress`` 接缝（“MemoryStore 不是
Provider”的缺口，计划 §1.6）。

§1.3 曾刻意保持精简（仅读/接缝路径）；§1.5 点亮写工具：
- 策展的冻结快照经 §1.1 ``memory_snapshot`` 槽位直接进入系统提示（装配顺序，计划 §1.1），故此处
  ``system_prompt_block`` 返回 ``""``——返回快照会造成重复。
- ``prefetch`` 返回 ``""``（策展记忆在提示中是静态的；按查询召回是 §1.4 的向量 provider）。
- ``sync_turn`` 为空操作（策展记忆不按回合自动写入；写入经下方面向模型的受治理 ``memory`` 工具，而非后台 sync）。
- ``get_tool_schemas`` 在注入 §1.5 ``GovernanceGate``（``gate=``）时返回受治理的 ``memory`` 写工具；无门控时返回
  ``[]``（保留 §1.3 精简默认，向后兼容）。``handle_tool_call`` 以门控做预检（拒绝未标注/未同意/偏见写入），将校验后的
  治理头前缀到条目，再调用 §1.2 存储——故移植的 ``MemoryStore`` 不变，且 100% 被接受写入携带标签。
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from ...governance.labels import ConsentLabel, Provenance
from ...governance.namespace import DEFAULT_ORG, DEFAULT_TENANT
from ..provider import MemoryProvider
from ..store import MemoryStore

# The governed model-facing write tool (§1.5). Every write MUST carry provenance + a lawful-basis label;
# the handler runs the GovernanceGate before touching the §1.2 store.
MEMORY_TOOL_SCHEMA: Dict[str, Any] = {
    "name": "memory",
    "description": (
        "Add, replace, or remove a curated organisational ('org') or recruiter ('recruiter') memory "
        "entry. Every write MUST carry provenance (source_type + source_ref) and a lawful-basis label; "
        "writes that lack them, or that reference protected attributes / proxy variables, are rejected."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["add", "replace", "remove"]},
            "target": {"type": "string", "enum": ["org", "recruiter"]},
            "content": {"type": "string", "description": "The entry body (for add/replace)."},
            "old_text": {"type": "string", "description": "Unique substring of the entry (for replace/remove)."},
            "source_type": {"type": "string", "description": "e.g. recruiter_input, candidate_submitted, public_jd."},
            "source_ref": {"type": "string", "description": "Pointer back to the original evidence (required)."},
            "legal_basis": {"type": "string", "enum": ["consent", "legitimate_interest", "contract"]},
            "purpose": {"type": "string"},
            "consent_id": {"type": "string", "description": "Required when source_type needs consent."},
            "retention_policy": {"type": "string", "description": "e.g. hired_5y, not_hired_180d."},
        },
        "required": ["action", "target"],
    },
}


class BuiltinMemoryProvider(MemoryProvider):
    """A ``MemoryProvider`` over the §1.2 curated ``MemoryStore`` (name ``"builtin"``).

    EN —
    Always registered first in the Manager. Lean by design in §1.3 (see the module
    docstring); the dynamic paths (recall §1.4, governed writes §1.5, real
    pre-compression extraction §1.6) light up later behind this same interface.

    中文 —
    在 Manager 中始终最先注册。§1.3 中按设计精简（见模块文档）；动态路径（召回 §1.4、受治理写入 §1.5、
    真实压缩前抽取 §1.6）随后在同一接口背后启用。
    """

    # Curated entries use named-constant keys at org/recruiter level (Plan §1.0): the single-tenant
    # MVP placeholders. The governed write tool stamps provenance.memory_key from these.
    _TARGET_KEYS = {
        "org": f"{DEFAULT_TENANT}:{DEFAULT_ORG}:org:policy",
        "recruiter": f"{DEFAULT_TENANT}:{DEFAULT_ORG}:recruiter:prefs",
    }

    def __init__(self, store: MemoryStore, *, gate: Optional[Any] = None, actor: str = "system") -> None:
        """Wrap a loaded ``MemoryStore``; optionally enable the governed write tool.

        EN —
        Args: store — a §1.2 store (already ``load_from_disk()``-ed by the composition root); gate — an
        optional §1.5 ``GovernanceGate`` (when supplied, the governed ``memory`` write tool is exposed
        and enforced; when ``None``, the §1.3 lean read/seam-only behaviour is preserved); actor — the
        audit actor (overridden by ``agent_identity`` at ``initialize``).

        中文 —
        参数：store——§1.2 存储（已由组合根 ``load_from_disk()``）；gate——可选的 §1.5 ``GovernanceGate``（提供时暴露并
        强制受治理的 ``memory`` 写工具；为 ``None`` 时保留 §1.3 仅读/接缝行为）；actor——审计执行者（在 ``initialize`` 由
        ``agent_identity`` 覆盖）。
        """
        self._store = store
        self._gate = gate
        self._actor = actor

    @property
    def name(self) -> str:
        """Provider name (always ``"builtin"``, registered first).

        EN: Returns: ``"builtin"``.
        中文：返回：``"builtin"``。
        """
        return "builtin"

    @property
    def store(self) -> MemoryStore:
        """The wrapped §1.2 store (for the composition root to read the snapshot).

        EN: Returns: the underlying ``MemoryStore``.
        中文：返回：底层 ``MemoryStore``。
        """
        return self._store

    def is_available(self) -> bool:
        """Local file store is always available.

        EN: Returns: True.
        中文：返回：True。
        """
        return True

    def initialize(self, session_id: str, **kwargs) -> None:
        """Capture the audit actor from ``agent_identity`` (the store is already loaded).

        EN: Args: session_id; kwargs (``agent_identity`` becomes the audit actor if present). Returns: None.
        中文：参数：session_id；kwargs（若有 ``agent_identity`` 则作为审计执行者）。返回：None。
        """
        identity = kwargs.get("agent_identity")
        if identity:
            self._actor = identity
        return None

    def system_prompt_block(self) -> str:
        """Empty — the snapshot reaches the prompt via the ``memory_snapshot`` slot, not here.

        EN: Returns: ``""`` (avoids duplicating the §1.2 frozen snapshot). See the module docstring.
        中文：返回：``""``（避免重复 §1.2 冻结快照）。见模块文档。
        """
        return ""

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        """Empty — curated memory is static in the prompt; per-query recall is §1.4.

        EN: Args: query; session_id (ignored). Returns: ``""``.
        中文：参数：query；session_id（忽略）。返回：``""``。
        """
        return ""

    def sync_turn(
        self,
        user_content: str,
        assistant_content: str,
        *,
        session_id: str = "",
        messages: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """No-op — curated memory is hand-edited; the governed write tool is §1.5.

        EN: Args: user_content; assistant_content; session_id; messages (ignored). Returns: None.
        中文：参数：user_content；assistant_content；session_id；messages（忽略）。返回：None。
        """
        return None

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """The governed ``memory`` write tool when a gate is injected, else ``[]`` (§1.3 default).

        EN: Returns: ``[MEMORY_TOOL_SCHEMA]`` if a §1.5 gate is present, else ``[]``.
        中文：返回：若有 §1.5 门控则 ``[MEMORY_TOOL_SCHEMA]``，否则 ``[]``。
        """
        return [MEMORY_TOOL_SCHEMA] if self._gate is not None else []

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        """Run the governed ``memory`` write: gate pre-check → header → §1.2 store → audit the commit.

        EN —
        Args: tool_name (must be ``"memory"``); args (action/target/content/old_text + governance label
        fields); kwargs (ignored). Returns: a JSON string — on rejection ``{"success": false, "rejected":
        <code>, "code": <full>}`` (the gate already audited it); on a committed write the §1.2 store's
        success dict, after recording ``write:<action>`` / ``ok``. Falls back to the base behaviour when
        no gate is configured or the tool is unknown.

        中文 —
        参数：tool_name（须为 ``"memory"``）；args（action/target/content/old_text + 治理标签字段）；kwargs（忽略）。
        返回：JSON 字符串——拒绝时 ``{"success": false, "rejected": <码>, "code": <全码>}``（门控已审计）；提交成功时为
        §1.2 存储的成功字典，并先记录 ``write:<action>`` / ``ok``。无门控或未知工具时回退到基类行为。
        """
        if tool_name != "memory" or self._gate is None:
            return super().handle_tool_call(tool_name, args, **kwargs)
        action = str(args.get("action") or "")
        if action not in ("add", "replace", "remove"):
            return json.dumps({"success": False, "error": f"unknown action {action!r}"})
        target = str(args.get("target") or "org")
        if target not in self._TARGET_KEYS:
            return json.dumps({"success": False, "error": f"unknown target {target!r}"})
        body = str(args.get("content") or "")
        key = self._TARGET_KEYS[target]
        prov = Provenance(key, str(args.get("source_type") or ""), str(args.get("source_ref") or ""),
                          collected_by=self._actor)
        consent = ConsentLabel(str(args.get("legal_basis") or "legitimate_interest"),
                               str(args.get("purpose") or ""), str(args.get("consent_id") or ""))
        retention_key = str(args.get("retention_policy") or "not_hired_180d")
        decision = self._gate.validate(action, key, body, prov, consent, retention_key, actor=self._actor)
        if not decision.ok:
            return json.dumps({"success": False, "rejected": decision.code.split(":", 1)[-1],
                               "code": decision.code})
        if action == "remove":
            result = self._store.remove(target, str(args.get("old_text") or ""))
        elif action == "replace":
            result = self._store.replace(target, str(args.get("old_text") or ""), decision.header + body)
        else:
            result = self._store.add(target, decision.header + body)
        if result.get("success"):
            self._gate.audit.record(self._actor, f"write:{action}", key, result="ok")
        else:
            # The gate passed but the ported §1.2 store rejected (drift → .bak, over-budget, ambiguous
            # match, duplicate). Leave an audit trail too (forensic completeness; Plan §1.5 drift row).
            code = "rejected:drift" if result.get("drift_backup") else "rejected:store"
            self._gate.audit.record(self._actor, f"write:{action}", key,
                                    reason=str(result.get("error") or "")[:200], result=code)
        return json.dumps(result)

    def on_pre_compress(self, messages: List[Dict[str, Any]]) -> str:
        """Participate in the §1.6 pre-compression lifecycle (the file store has the hook) — returns "".

        EN —
        §1.6 fixes the call-site gap (the Manager aggregates this and the loop now captures + merges it),
        and the builtin file-backed provider IS driven by that aggregation — so "file-backed memory takes
        part" is satisfied at the lifecycle/seam level. It returns ``""`` because **curated Org/Recruiter
        memory is hand-edited, not conversation-derived** — there is nothing for *this* provider to extract
        from the about-to-be-discarded messages. Extracting key facts from the *conversation* is a distinct
        concern (the abstractive LLM summariser / a future conversation-memory provider) and lands at §1.11;
        §1.6 ships the wiring, not conversation content-extraction.
        Args: messages (about to be compressed). Returns: ``""``.

        中文 —
        §1.6 修复调用点缺口（Manager 聚合此值，循环现已捕获 + 并入），且内置文件型 provider 确由该聚合驱动——故
        “文件型记忆参与”在生命周期/接缝层面已满足。它返回 ``""``，因为**策展 Org/Recruiter 记忆是人工编辑、并非由对话派生**
        ——本 provider 无可从即将丢弃的消息中抽取之物。从*对话*抽取关键事实是另一关注点（抽象式 LLM 摘要器 / 未来的对话
        记忆 provider），落在 §1.11；§1.6 交付接线，而非对话内容抽取。参数：messages（即将被压缩）。返回：``""``。
        """
        return ""

    def shutdown(self) -> None:
        """No-op (no resources held).

        EN: Returns: None.
        中文：返回：None。
        """
        return None
