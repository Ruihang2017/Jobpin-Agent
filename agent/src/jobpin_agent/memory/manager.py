"""MemoryManager — orchestrates memory providers for the agent (ported from Hermes, MIT).

EN —
Ported from Hermes ``agent/memory_manager.py::MemoryManager``. One integration
point that drives every registered provider through its lifecycle and gives the
agent loop a uniform memory API: build the system-prompt block, prefetch recall
before a turn, sync the turn afterwards on a serial background worker, route the
provider tool calls, and tear down cleanly. Failures in one provider never block
the others or the turn (try/except + log everywhere). Only ONE external (non-
builtin) provider is allowed (Phase 2 relaxes this with ``CompositeMemoryProvider``).

What changed vs Hermes (TEXTBOOK_SPEC Tenet 1) — the §1.3 trims, behaviour
otherwise identical:
- ``_strip_skill_scaffolding`` is a pass-through (Jobpin has no /skill layer); the
  seam is kept so a skill layer can plug in later.
- local ``tool_error`` (Hermes imported it from ``tools.registry``).
- ``_CORE_TOOL_NAMES`` is a local frozenset (Hermes imported ``_HERMES_CORE_TOOLS``
  from ``toolsets``); it is the reserved set the registry extends.
- ``initialize_all`` forwards kwargs as-is (no ``hermes_home`` injection).
- ``StreamingContextScrubber``, ``inject_memory_provider_tools`` and
  ``memory_provider_tools_enabled`` are NOT ported here (streaming/agent-surface
  wiring lands at §1.6 / §1.5). The fence helpers live in ``memory/fence.py``.

中文 —
移植自 Hermes ``agent/memory_manager.py::MemoryManager``。单一集成点，驱动每个已注册 provider 走完其生命周期，
并给 agent 循环统一的记忆 API：构建系统提示块、回合前 prefetch 召回、回合后在串行后台工作线程 sync、路由
provider 工具调用、并干净拆解。某个 provider 失败绝不阻塞其他 provider 或当前回合（处处 try/except + 记录）。
只允许一个外部（非 builtin）provider（第二阶段以 ``CompositeMemoryProvider`` 放宽）。

相对 Hermes 的改动（TEXTBOOK_SPEC 第一原则）——§1.3 裁剪，其余行为一致：
- ``_strip_skill_scaffolding`` 为直通（Jobpin 无 /skill 层）；接缝保留以便日后接入技能层。
- 本地 ``tool_error``（Hermes 从 ``tools.registry`` 导入）。
- ``_CORE_TOOL_NAMES`` 为本地 frozenset（Hermes 从 ``toolsets`` 导入 ``_HERMES_CORE_TOOLS``）；为注册表扩展的保留集合。
- ``initialize_all`` 原样转发 kwargs（不注入 ``hermes_home``）。
- ``StreamingContextScrubber``、``inject_memory_provider_tools`` 与 ``memory_provider_tools_enabled`` 此处不移植
  （流式/agent 表面接线在 §1.6 / §1.5）。围栏助手位于 ``memory/fence.py``。
"""
from __future__ import annotations

import inspect
import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional

from .provider import MemoryProvider

logger = logging.getLogger(__name__)

# How long shutdown_all() waits for in-flight background sync/prefetch work to
# drain before abandoning it. A wedged provider must never block teardown — the
# worker is daemon, so anything still running past this window dies with the
# interpreter. (Ported verbatim from Hermes.)
_SYNC_DRAIN_TIMEOUT_S = 5.0

# Reserved core tool names a provider must never shadow (built-ins always win).
# Jobpin-local replacement for Hermes's ``_HERMES_CORE_TOOLS``; extend as the core
# tool surface grows. The §1.5 governed memory tool registers OUTSIDE this set.
_CORE_TOOL_NAMES = frozenset({"clarify", "delegate_task"})


def tool_error(message: str) -> str:
    """Build a JSON tool-error string (Jobpin-local; Hermes imported this).

    EN: Args: message. Returns: ``{"success": false, "error": message}`` as JSON.
    中文：参数：message。返回：JSON 形式的 ``{"success": false, "error": message}``。
    """
    return json.dumps({"success": False, "error": message})


def normalize_tool_schema(schema: Any) -> Optional[Dict[str, Any]]:
    """Return a function-tool dict with a resolvable top-level ``name`` (ported).

    EN —
    Providers may return a bare function schema (``{"name", "description",
    "parameters"}``) or one already wrapped as ``{"type": "function", "function":
    {...}}``. This normalises both to the bare schema and returns ``None`` for
    anything without a resolvable name, so callers skip-with-warning rather than
    advertising a nameless tool (which strict backends reject with HTTP 400).
    Args: schema. Returns: the bare schema dict, or ``None``.

    中文 —
    provider 可能返回裸函数 schema（``{"name", "description", "parameters"}``）或已包成
    ``{"type": "function", "function": {...}}`` 的形态。本函数将两者归一为裸 schema，对任何无可解析名称者返回
    ``None``，使调用方“跳过并告警”而非告知一个无名工具（严格后端会以 HTTP 400 拒绝）。
    参数：schema。返回：裸 schema 字典，或 ``None``。
    """
    if not isinstance(schema, dict):
        return None
    if schema.get("type") == "function" and isinstance(schema.get("function"), dict):
        schema = schema["function"]
        if not isinstance(schema, dict):
            return None
    name = schema.get("name", "")
    if not name or not isinstance(name, str):
        return None
    return schema


class MemoryManager:
    """Orchestrates the built-in provider plus at most one external provider (ported).

    EN —
    The builtin provider is always first; only one non-builtin provider is allowed.
    A failure in one provider never blocks another or the turn. Background sync /
    prefetch run on a single-worker daemon executor (serial: turn N before N+1).

    中文 —
    builtin provider 始终最先；仅允许一个非 builtin provider。某 provider 的失败绝不阻塞其他 provider 或回合。
    后台 sync / prefetch 在单工作线程守护执行器上运行（串行：第 N 回合先于第 N+1 回合）。
    """

    def __init__(self) -> None:
        """Construct an empty manager (the executor is created lazily on first use).

        EN: Returns: None.
        中文：返回：None。
        """
        self._providers: List[MemoryProvider] = []
        self._tool_to_provider: Dict[str, MemoryProvider] = {}
        self._has_external: bool = False
        self._sync_executor: Optional[ThreadPoolExecutor] = None
        self._sync_executor_lock = threading.Lock()

    # -- Registration --------------------------------------------------------

    def add_provider(self, provider: MemoryProvider) -> None:
        """Register a provider (builtin always; one external max; shadow-guarded) (ported).

        EN —
        ``builtin`` is always accepted. A second external (non-builtin) provider is
        rejected with a warning (schema bloat / backend conflict). A provider tool
        whose name is in ``_CORE_TOOL_NAMES`` is dropped at the door so it never
        enters the routing table (built-ins always win).
        Args: provider. Returns: None.

        中文 —
        ``builtin`` 始终接受。第二个外部（非 builtin）provider 被告警拒绝（schema 膨胀 / 后端冲突）。名称在
        ``_CORE_TOOL_NAMES`` 中的 provider 工具在门口即被丢弃，绝不进入路由表（内置始终胜出）。
        参数：provider。返回：None。
        """
        is_builtin = provider.name == "builtin"
        if not is_builtin:
            if self._has_external:
                existing = next((p.name for p in self._providers if p.name != "builtin"), "unknown")
                logger.warning(
                    "Rejected memory provider '%s' — external provider '%s' is already registered. "
                    "Only one external memory provider is allowed at a time.",
                    provider.name, existing,
                )
                return
            self._has_external = True

        self._providers.append(provider)

        for raw_schema in provider.get_tool_schemas():
            schema = normalize_tool_schema(raw_schema)
            if schema is None:
                continue
            tool_name = schema["name"]
            if tool_name in _CORE_TOOL_NAMES:
                logger.warning(
                    "Memory provider '%s' tool '%s' shadows a reserved core tool name; "
                    "registration ignored. Core tools always win — rename the provider's tool.",
                    provider.name, tool_name,
                )
                continue
            if tool_name and tool_name not in self._tool_to_provider:
                self._tool_to_provider[tool_name] = provider
            elif tool_name in self._tool_to_provider:
                logger.warning(
                    "Memory tool name conflict: '%s' already registered by %s, ignoring from %s",
                    tool_name, self._tool_to_provider[tool_name].name, provider.name,
                )

        logger.info("Memory provider '%s' registered (%d tools)", provider.name, len(provider.get_tool_schemas()))

    @property
    def providers(self) -> List[MemoryProvider]:
        """All registered providers in order.

        EN: Returns: a copy of the provider list.
        中文：返回：provider 列表的副本。
        """
        return list(self._providers)

    def get_provider(self, name: str) -> Optional[MemoryProvider]:
        """Look up a provider by name.

        EN: Args: name. Returns: the provider, or None.
        中文：参数：name。返回：provider，或 None。
        """
        for p in self._providers:
            if p.name == name:
                return p
        return None

    # -- System prompt -------------------------------------------------------

    def build_system_prompt(self) -> str:
        """Collect static system-prompt blocks from all providers (ported).

        EN: Returns: the non-empty blocks joined by blank lines (or ``""``). Failure-isolated.
        中文：返回：以空行连接的非空块（或 ``""``）。失败隔离。
        """
        blocks = []
        for provider in self._providers:
            try:
                block = provider.system_prompt_block()
                if block and block.strip():
                    blocks.append(block)
            except Exception as e:
                logger.warning("Memory provider '%s' system_prompt_block() failed: %s", provider.name, e)
        return "\n\n".join(blocks)

    # -- Prefetch / recall ---------------------------------------------------

    @staticmethod
    def _strip_skill_scaffolding(text: str) -> Optional[str]:
        """Return memory-worthy user text (Jobpin pass-through; Hermes stripped /skill bodies).

        EN: Args: text. Returns: ``text`` unchanged (seam kept for a future skill layer).
        中文：参数：text。返回：原样的 ``text``（为未来技能层保留接缝）。
        """
        return text

    def prefetch_all(self, query: str, *, session_id: str = "") -> str:
        """Collect prefetch recall from all providers (ported).

        EN: Args: query; session_id. Returns: merged recall text (blank-line joined), or ``""``.
            Failure-isolated (one provider's error is non-fatal).
        中文：参数：query；session_id。返回：合并的召回文本（空行连接），或 ``""``。失败隔离（某 provider 错误非致命）。
        """
        clean_query = self._strip_skill_scaffolding(query)
        if not clean_query:
            return ""
        parts = []
        for provider in self._providers:
            try:
                result = provider.prefetch(clean_query, session_id=session_id)
                if result and result.strip():
                    parts.append(result)
            except Exception as e:
                logger.debug("Memory provider '%s' prefetch failed (non-fatal): %s", provider.name, e)
        return "\n\n".join(parts)

    def queue_prefetch_all(self, query: str, *, session_id: str = "") -> None:
        """Queue background prefetch on all providers for the next turn (ported).

        EN: Args: query; session_id. Returns: None. Dispatched to the background worker.
        中文：参数：query；session_id。返回：None。派发到后台工作线程。
        """
        providers = list(self._providers)
        if not providers:
            return
        clean_query = self._strip_skill_scaffolding(query)
        if not clean_query:
            return

        def _run() -> None:
            for provider in providers:
                try:
                    provider.queue_prefetch(clean_query, session_id=session_id)
                except Exception as e:
                    logger.debug("Memory provider '%s' queue_prefetch failed (non-fatal): %s", provider.name, e)

        self._submit_background(_run)

    # -- Sync ----------------------------------------------------------------

    @staticmethod
    def _provider_sync_accepts_messages(provider: MemoryProvider) -> bool:
        """Whether the provider's ``sync_turn`` accepts a ``messages`` keyword (ported).

        EN: Args: provider. Returns: True if it has ``messages`` or ``**kwargs``.
        中文：参数：provider。返回：若其有 ``messages`` 或 ``**kwargs`` 则 True。
        """
        try:
            signature = inspect.signature(provider.sync_turn)
        except (TypeError, ValueError):
            return True
        params = list(signature.parameters.values())
        if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params):
            return True
        return "messages" in signature.parameters

    def sync_all(
        self,
        user_content: str,
        assistant_content: str,
        *,
        session_id: str = "",
        messages: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Sync a completed turn to all providers on the background worker (ported).

        EN —
        Runs off-thread so a slow/blocking provider can never stall the turn. Writes
        are serialised through the single worker so turn N lands before N+1.
        Args: user_content; assistant_content; session_id; messages. Returns: None.

        中文 —
        在后台线程运行，使慢/阻塞的 provider 绝不拖住回合。写入经单工作线程串行化，使第 N 回合先于第 N+1 回合落地。
        参数：user_content；assistant_content；session_id；messages。返回：None。
        """
        providers = list(self._providers)
        if not providers:
            return
        clean_user_content = self._strip_skill_scaffolding(user_content)
        if not clean_user_content:
            return
        user_content = clean_user_content

        def _run() -> None:
            for provider in providers:
                try:
                    if messages is not None and self._provider_sync_accepts_messages(provider):
                        provider.sync_turn(user_content, assistant_content, session_id=session_id, messages=messages)
                    else:
                        provider.sync_turn(user_content, assistant_content, session_id=session_id)
                except Exception as e:
                    logger.warning("Memory provider '%s' sync_turn failed: %s", provider.name, e)

        self._submit_background(_run)

    # -- Background dispatch -------------------------------------------------

    def _submit_background(self, fn) -> None:
        """Run ``fn`` on the manager's background worker, falling back to inline (ported).

        EN: Args: fn (does its own per-provider error handling). Returns: None.
        中文：参数：fn（自行处理各 provider 错误）。返回：None。
        """
        executor = self._get_sync_executor()
        if executor is None:
            try:
                fn()
            except Exception as e:  # pragma: no cover - fn guards internally
                logger.debug("Inline memory background task failed: %s", e)
            return
        try:
            executor.submit(fn)
        except RuntimeError:
            try:
                fn()
            except Exception as e:  # pragma: no cover - fn guards internally
                logger.debug("Inline memory background task failed: %s", e)

    def _get_sync_executor(self) -> Optional[ThreadPoolExecutor]:
        """Lazily create the single-worker background executor (ported).

        EN: Returns: the ``mem-sync`` executor (``max_workers=1``), or None on failure.
        中文：返回：``mem-sync`` 执行器（``max_workers=1``），失败则 None。
        """
        if self._sync_executor is not None:
            return self._sync_executor
        with self._sync_executor_lock:
            if self._sync_executor is None:
                try:
                    self._sync_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mem-sync")
                except Exception as e:  # pragma: no cover - resource exhaustion
                    logger.warning("Failed to create memory sync executor: %s", e)
                    return None
            return self._sync_executor

    def flush_pending(self, timeout: Optional[float] = None) -> bool:
        """Block until queued sync/prefetch work has drained (a barrier) (ported).

        EN —
        The single worker means a sentinel submitted now runs after every prior
        task. Used at real session boundaries and by tests to assert provider state.
        Args: timeout. Returns: True if drained (or no executor), False on timeout.

        中文 —
        单工作线程意味着此刻提交的哨兵会在所有先前任务之后运行。用于真实会话边界与测试断言 provider 状态。
        参数：timeout。返回：已排空（或无执行器）则 True，超时则 False。
        """
        executor = self._sync_executor
        if executor is None:
            return True
        try:
            fut = executor.submit(lambda: None)
        except RuntimeError:
            return True
        try:
            fut.result(timeout=timeout)
            return True
        except Exception:
            return False

    # -- Tools ---------------------------------------------------------------

    def get_all_tool_schemas(self) -> List[Dict[str, Any]]:
        """Collect tool schemas from all providers, skipping reserved core names (ported).

        EN: Returns: deduped bare schemas (core-name and nameless schemas dropped).
        中文：返回：去重的裸 schema（丢弃核心名与无名 schema）。
        """
        schemas = []
        seen = set()
        for provider in self._providers:
            try:
                for raw_schema in provider.get_tool_schemas():
                    schema = normalize_tool_schema(raw_schema)
                    if schema is None:
                        logger.warning(
                            "Memory provider '%s' returned a tool schema with no resolvable name; skipping (%r)",
                            provider.name, raw_schema,
                        )
                        continue
                    name = schema["name"]
                    if name in _CORE_TOOL_NAMES:
                        continue
                    if name not in seen:
                        schemas.append(schema)
                        seen.add(name)
            except Exception as e:
                logger.warning("Memory provider '%s' get_tool_schemas() failed: %s", provider.name, e)
        return schemas

    def get_all_tool_names(self) -> set:
        """All tool names across all providers (routing table keys).

        EN: Returns: the set of routable tool names.
        中文：返回：可路由工具名集合。
        """
        return set(self._tool_to_provider.keys())

    def has_tool(self, tool_name: str) -> bool:
        """Whether any provider handles this tool.

        EN: Args: tool_name. Returns: True if routable.
        中文：参数：tool_name。返回：可路由则 True。
        """
        return tool_name in self._tool_to_provider

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        """Route a tool call to the owning provider (ported).

        EN: Args: tool_name; args; kwargs. Returns: the provider's JSON result, or a
            ``tool_error`` JSON string (unknown tool / provider raised).
        中文：参数：tool_name；args；kwargs。返回：provider 的 JSON 结果，或 ``tool_error`` JSON 字符串
            （未知工具 / provider 抛错）。
        """
        provider = self._tool_to_provider.get(tool_name)
        if provider is None:
            return tool_error(f"No memory provider handles tool '{tool_name}'")
        try:
            return provider.handle_tool_call(tool_name, args, **kwargs)
        except Exception as e:
            logger.error("Memory provider '%s' handle_tool_call(%s) failed: %s", provider.name, tool_name, e)
            return tool_error(f"Memory tool '{tool_name}' failed: {e}")

    # -- Lifecycle hooks -----------------------------------------------------

    def on_turn_start(self, turn_number: int, message: str, **kwargs) -> None:
        """Notify all providers of a new turn (ported, failure-isolated).

        EN: Args: turn_number; message; kwargs. Returns: None.
        中文：参数：turn_number；message；kwargs。返回：None。
        """
        for provider in self._providers:
            try:
                provider.on_turn_start(turn_number, message, **kwargs)
            except Exception as e:
                logger.debug("Memory provider '%s' on_turn_start failed: %s", provider.name, e)

    def on_session_end(self, messages: List[Dict[str, Any]]) -> None:
        """Notify all providers of session end (ported, failure-isolated).

        EN: Args: messages (full history). Returns: None.
        中文：参数：messages（完整历史）。返回：None。
        """
        for provider in self._providers:
            try:
                provider.on_session_end(messages)
            except Exception as e:
                logger.warning("Memory provider '%s' on_session_end failed: %s", provider.name, e, exc_info=True)

    def on_session_switch(
        self,
        new_session_id: str,
        *,
        parent_session_id: str = "",
        reset: bool = False,
        rewound: bool = False,
        **kwargs,
    ) -> None:
        """Notify all providers the session_id rotated (ported, failure-isolated).

        EN —
        ``rewound`` is forwarded only when set (passing ``rewound=False`` would
        pollute providers that capture extra kwargs / break exact-dict assertions).
        Args: new_session_id; parent_session_id; reset; rewound; kwargs. Returns: None.

        中文 —
        ``rewound`` 仅在为真时转发（传 ``rewound=False`` 会污染捕获额外 kwargs 的 provider / 破坏精确字典断言）。
        参数：new_session_id；parent_session_id；reset；rewound；kwargs。返回：None。
        """
        if not new_session_id:
            return
        if rewound:
            kwargs["rewound"] = True
        for provider in self._providers:
            try:
                provider.on_session_switch(new_session_id, parent_session_id=parent_session_id, reset=reset, **kwargs)
            except Exception as e:
                logger.debug("Memory provider '%s' on_session_switch failed: %s", provider.name, e)

    def on_pre_compress(self, messages: List[Dict[str, Any]]) -> str:
        """Aggregate providers' pre-compression facts (ported, failure-isolated).

        EN —
        Already aggregates + joins the providers' return values (the §1.6 wiring is
        only the compression CALL SITE capturing this — Plan §1.6).
        Args: messages. Returns: joined facts to retain, or ``""``.

        中文 —
        已聚合并连接各 provider 的返回值（§1.6 接线仅是压缩调用点捕获此值——计划 §1.6）。
        参数：messages。返回：要保留的连接事实，或 ``""``。
        """
        parts = []
        for provider in self._providers:
            try:
                result = provider.on_pre_compress(messages)
                if result and result.strip():
                    parts.append(result)
            except Exception as e:
                logger.debug("Memory provider '%s' on_pre_compress failed: %s", provider.name, e)
        return "\n\n".join(parts)

    @staticmethod
    def _provider_memory_write_metadata_mode(provider: MemoryProvider) -> str:
        """How to pass metadata to a provider's ``on_memory_write`` (ported).

        EN: Args: provider. Returns: "keyword" / "positional" / "legacy".
        中文：参数：provider。返回："keyword" / "positional" / "legacy"。
        """
        try:
            signature = inspect.signature(provider.on_memory_write)
        except (TypeError, ValueError):
            return "keyword"
        params = list(signature.parameters.values())
        if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params):
            return "keyword"
        if "metadata" in signature.parameters:
            return "keyword"
        accepted = [
            p for p in params
            if p.kind in {inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY}
        ]
        if len(accepted) >= 4:
            return "positional"
        return "legacy"

    def on_memory_write(
        self,
        action: str,
        target: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Notify external providers of a built-in memory write (ported, skips builtin).

        EN: Args: action; target; content; metadata. Returns: None. Relevant in Phase 2.
        中文：参数：action；target；content；metadata。返回：None。第二阶段相关。
        """
        for provider in self._providers:
            if provider.name == "builtin":
                continue
            try:
                metadata_mode = self._provider_memory_write_metadata_mode(provider)
                if metadata_mode == "keyword":
                    provider.on_memory_write(action, target, content, metadata=dict(metadata or {}))
                elif metadata_mode == "positional":
                    provider.on_memory_write(action, target, content, dict(metadata or {}))
                else:
                    provider.on_memory_write(action, target, content)
            except Exception as e:
                logger.debug("Memory provider '%s' on_memory_write failed: %s", provider.name, e)

    _MIRRORED_MEMORY_ACTIONS = {"add", "replace", "remove"}

    @staticmethod
    def _memory_tool_result_succeeded(result: Any) -> bool:
        """True only when a built-in memory tool actually committed a write (ported, fail-closed).

        EN: Args: result (JSON string or dict). Returns: True iff ``success`` and not ``staged``.
        中文：参数：result（JSON 字符串或 dict）。返回：当且仅当 ``success`` 且非 ``staged`` 时为 True。
        """
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except Exception:
                return False
        if not isinstance(result, dict):
            return False
        return result.get("success") is True and result.get("staged") is not True

    def notify_memory_tool_write(
        self,
        tool_result: Any,
        tool_args: Dict[str, Any],
        *,
        build_metadata: Optional[Callable[[], Dict[str, Any]]] = None,
    ) -> None:
        """Mirror a committed built-in memory tool call to external providers (ported).

        EN —
        The single entry point the loop calls after the built-in ``memory`` tool runs
        (wired live at §1.5). Gates on a committed write, expands single/batched
        shapes, keeps add/replace/remove, builds per-op provenance.
        Args: tool_result; tool_args; build_metadata. Returns: None.

        中文 —
        循环在内置 ``memory`` 工具运行后调用的单一入口（§1.5 启用）。以已提交写入为门，展开单/批形态，
        保留 add/replace/remove，构建逐操作来源。参数：tool_result；tool_args；build_metadata。返回：None。
        """
        if not self._memory_tool_result_succeeded(tool_result):
            return
        target = str(tool_args.get("target") or "memory")
        operations = tool_args.get("operations")
        if isinstance(operations, list) and operations:
            raw_operations = operations
        else:
            raw_operations = [{
                "action": tool_args.get("action"),
                "content": tool_args.get("content"),
                "old_text": tool_args.get("old_text"),
            }]
        for op in raw_operations:
            if not isinstance(op, dict):
                continue
            action = str(op.get("action") or "")
            if action not in self._MIRRORED_MEMORY_ACTIONS:
                continue
            try:
                metadata = dict(build_metadata() if build_metadata else {})
                old_text = op.get("old_text")
                if old_text:
                    metadata["old_text"] = str(old_text)
                self.on_memory_write(action, target, str(op.get("content") or ""), metadata=metadata)
            except Exception as e:
                logger.debug("notify_memory_tool_write failed for op %s: %s", action, e)

    def on_delegation(self, task: str, result: str, *, child_session_id: str = "", **kwargs) -> None:
        """Notify all providers that a subagent completed (ported, failure-isolated).

        EN: Args: task; result; child_session_id; kwargs. Returns: None.
        中文：参数：task；result；child_session_id；kwargs。返回：None。
        """
        for provider in self._providers:
            try:
                provider.on_delegation(task, result, child_session_id=child_session_id, **kwargs)
            except Exception as e:
                logger.debug("Memory provider '%s' on_delegation failed: %s", provider.name, e)

    def shutdown_all(self) -> None:
        """Drain the background executor (bounded) then shut down providers (ported).

        EN: Returns: None. A wedged provider cannot hang teardown (daemon worker + bounded drain).
        中文：返回：None。被卡住的 provider 无法拖住拆解（守护工作线程 + 有界排空）。
        """
        self._drain_sync_executor()
        for provider in reversed(self._providers):
            try:
                provider.shutdown()
            except Exception as e:
                logger.warning("Memory provider '%s' shutdown failed: %s", provider.name, e)

    def _drain_sync_executor(self) -> None:
        """Shut down the background executor, waiting at most the drain timeout (ported).

        EN: Returns: None. Cancels queued work; an in-flight task gets ``_SYNC_DRAIN_TIMEOUT_S`` on a daemon watcher.
        中文：返回：None。取消排队任务；在飞任务在守护监视线程上获得 ``_SYNC_DRAIN_TIMEOUT_S``。
        """
        with self._sync_executor_lock:
            executor = self._sync_executor
            self._sync_executor = None
        if executor is None:
            return
        try:
            executor.shutdown(wait=False, cancel_futures=True)
        except TypeError:
            try:
                executor.shutdown(wait=False)
            except Exception as e:  # pragma: no cover
                logger.debug("Memory sync executor shutdown failed: %s", e)
            return
        except Exception as e:  # pragma: no cover
            logger.debug("Memory sync executor shutdown failed: %s", e)
            return
        drainer = threading.Thread(
            target=lambda: self._bounded_executor_wait(executor),
            daemon=True,
            name="mem-sync-drain",
        )
        drainer.start()
        drainer.join(timeout=_SYNC_DRAIN_TIMEOUT_S)

    @staticmethod
    def _bounded_executor_wait(executor: ThreadPoolExecutor) -> None:
        """Wait for the executor to fully drain (run on a daemon watcher) (ported).

        EN: Args: executor. Returns: None.
        中文：参数：executor。返回：None。
        """
        try:
            executor.shutdown(wait=True)
        except Exception as e:  # pragma: no cover
            logger.debug("Memory sync executor drain wait failed: %s", e)

    def initialize_all(self, session_id: str, **kwargs) -> None:
        """Initialize all providers (ported; no ``hermes_home`` injection — §1.3 trim).

        EN: Args: session_id; kwargs (forwarded as-is). Returns: None. Failure-isolated.
        中文：参数：session_id；kwargs（原样转发）。返回：None。失败隔离。
        """
        for provider in self._providers:
            try:
                provider.initialize(session_id=session_id, **kwargs)
            except Exception as e:
                logger.warning("Memory provider '%s' initialize failed: %s", provider.name, e)
