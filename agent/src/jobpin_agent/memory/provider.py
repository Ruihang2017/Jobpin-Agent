"""Abstract base class for pluggable memory providers — ported from Hermes (MIT).

EN —
Ported from Hermes ``agent/memory_provider.py::MemoryProvider``. A provider gives
the agent persistent recall across sessions behind ONE uniform interface, so the
small-volume curated store (§1.2, the built-in provider) and the large-volume
retrieval stores (§1.4 candidate/semantic) look identical to the conversation
loop. The ``MemoryManager`` (§1.3) drives the lifecycle; this class is the contract
each backend implements.

Lifecycle (called by the Manager): ``initialize`` -> ``system_prompt_block`` (static
prompt text) -> ``prefetch`` (pre-turn recall) -> ``sync_turn`` (post-turn write) ->
``queue_prefetch`` (warm the next turn) -> ``shutdown``. Optional hooks
(``on_turn_start``/``on_session_end``/``on_session_switch``/``on_pre_compress``/
``on_delegation``/``on_memory_write``/``backup_paths``/config) are opt-in.

What changed vs Hermes (TEXTBOOK_SPEC Tenet 1): nothing structural — the contract
is ported as-is. The Hermes-specific ``hermes_home`` kwarg note is kept descriptive
only (the Manager no longer injects it; see §1.3 trims). The governed model-facing
write tool (``get_tool_schemas``/``handle_tool_call`` returning a real ``memory``
tool) lands at §1.5; the built-in provider returns ``[]`` here for now.

中文 —
移植自 Hermes ``agent/memory_provider.py::MemoryProvider``。provider 在单一统一接口背后为 agent 提供跨会话
持久召回，使小体量的策展存储（§1.2，内置 provider）与大体量的检索存储（§1.4 候选/语义）对会话循环看起来一致。
``MemoryManager``（§1.3）驱动其生命周期；本类是每个后端实现的契约。

生命周期（由 Manager 调用）：``initialize`` -> ``system_prompt_block``（静态提示文本）-> ``prefetch``（回合前召回）
-> ``sync_turn``（回合后写入）-> ``queue_prefetch``（预热下一回合）-> ``shutdown``。可选钩子
（``on_turn_start``/``on_session_end``/``on_session_switch``/``on_pre_compress``/``on_delegation``/
``on_memory_write``/``backup_paths``/配置）按需重写。

相对 Hermes 的改动（TEXTBOOK_SPEC 第一原则）：结构上无改动——契约原样移植。Hermes 特有的 ``hermes_home``
kwarg 说明仅作描述保留（Manager 不再注入它；见 §1.3 裁剪）。受治理的面向模型写工具
（``get_tool_schemas``/``handle_tool_call`` 返回真实 ``memory`` 工具）在 §1.5 落地；内置 provider 此处暂返回 ``[]``。
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MemoryProvider(ABC):
    """Abstract base class for memory providers (ported).

    EN —
    Implement the abstract members (``name``, ``is_available``, ``initialize``,
    ``get_tool_schemas``); override the opt-in hooks as needed. The Manager calls
    these at well-defined moments and isolates failures (one provider raising
    never blocks the others or the turn).

    中文 —
    实现抽象成员（``name``、``is_available``、``initialize``、``get_tool_schemas``）；按需重写可选钩子。Manager 在
    明确时机调用这些方法并隔离失败（某个 provider 抛错绝不阻塞其他 provider 或当前回合）。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier for this provider (e.g. ``"builtin"``).

        EN: Returns: the provider's stable name (``"builtin"`` is always first).
        中文：返回：provider 的稳定名称（``"builtin"`` 始终排在最前）。
        """

    # -- Core lifecycle (implement these) ------------------------------------

    @abstractmethod
    def is_available(self) -> bool:
        """Whether this provider is configured and ready (no network).

        EN: Returns: True if config/credentials/deps are present. Called at init.
        中文：返回：配置/凭据/依赖齐备则为 True。在初始化时调用。
        """

    @abstractmethod
    def initialize(self, session_id: str, **kwargs) -> None:
        """Initialize for a session (create resources, connect, warm up).

        EN —
        Args: session_id; kwargs may include ``platform``, ``agent_context``
            ("primary"/"subagent"/"cron"/"flush" — non-primary should skip writes,
            Invariant 3), ``agent_identity`` (audit actor), ``user_id`` (RBAC, §1.5).
        中文 —
        参数：session_id；kwargs 可含 ``platform``、``agent_context``（"primary"/"subagent"/"cron"/"flush"——
            非 primary 应跳过写入，不变量 3）、``agent_identity``（审计执行者）、``user_id``（RBAC，§1.5）。
        """

    def system_prompt_block(self) -> str:
        """Static text for the system prompt (NOT recall) (ported default).

        EN: Returns: static provider info, or ``""`` to skip. Recall goes via ``prefetch``.
        中文：返回：静态 provider 信息，或 ``""`` 跳过。召回经 ``prefetch``。
        """
        return ""

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        """Recall relevant context for the upcoming turn (ported default).

        EN: Args: query; session_id. Returns: formatted recall text, or ``""``.
            Must be fast (do heavy work in ``queue_prefetch`` and cache it).
        中文：参数：query；session_id。返回：格式化召回文本，或 ``""``。必须快（重活放入 ``queue_prefetch`` 并缓存）。
        """
        return ""

    def queue_prefetch(self, query: str, *, session_id: str = "") -> None:
        """Queue a background recall for the NEXT turn (ported default: no-op).

        EN: Args: query; session_id. Returns: None. Override to warm a cache.
        中文：参数：query；session_id。返回：None。重写以预热缓存。
        """

    def sync_turn(
        self,
        user_content: str,
        assistant_content: str,
        *,
        session_id: str = "",
        messages: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Persist a completed turn to the backend (ported default: no-op).

        EN: Args: user_content; assistant_content; session_id; messages (OpenAI-style
            list incl. tool calls/results). Should be non-blocking (the Manager runs
            this on a background worker).
        中文：参数：user_content；assistant_content；session_id；messages（OpenAI 风格列表，含工具调用/结果）。
            应非阻塞（Manager 在后台工作线程运行）。
        """

    @abstractmethod
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Tool schemas this provider exposes to the model (ported).

        EN: Returns: a list of OpenAI-style function schemas, or ``[]`` (context-only).
            The governed ``memory`` write tool is added at §1.5.
        中文：返回：OpenAI 风格函数 schema 列表，或 ``[]``（仅上下文）。受治理的 ``memory`` 写工具在 §1.5 加入。
        """

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        """Handle a tool call for one of this provider's tools (ported default).

        EN: Args: tool_name; args; kwargs. Returns: a JSON string result.
            Raises: NotImplementedError if the provider declares no such tool.
        中文：参数：tool_name；args；kwargs。返回：JSON 字符串结果。
            抛出：若 provider 未声明该工具则 NotImplementedError。
        """
        raise NotImplementedError(f"Provider {self.name} does not handle tool {tool_name}")

    def shutdown(self) -> None:
        """Clean shutdown — flush queues, close connections (ported default: no-op).

        EN: Returns: None.
        中文：返回：None。
        """

    # -- Optional hooks (override to opt in) ---------------------------------

    def on_turn_start(self, turn_number: int, message: str, **kwargs) -> None:
        """Per-turn tick with the user message (ported default: no-op).

        EN: Args: turn_number; message; kwargs (e.g. remaining_tokens, model). For turn-counting/maintenance.
        中文：参数：turn_number；message；kwargs（如 remaining_tokens、model）。用于回合计数/维护。
        """

    def on_session_end(self, messages: List[Dict[str, Any]]) -> None:
        """Session boundary (exit/timeout), not per-turn (ported default: no-op).

        EN: Args: messages (full history). For end-of-session extraction/summary.
        中文：参数：messages（完整历史）。用于会话结束时的抽取/摘要。
        """

    def on_session_switch(
        self,
        new_session_id: str,
        *,
        parent_session_id: str = "",
        reset: bool = False,
        rewound: bool = False,
        **kwargs,
    ) -> None:
        """The agent switched session_id mid-process (ported default: no-op).

        EN —
        Fires on resume/branch/reset/new and compression. Providers caching
        per-session state should refresh it so writes land in the right record.
        Args: new_session_id; parent_session_id (lineage for branch/resume/compression);
            reset (a genuinely new conversation — flush per-session buffers);
            rewound (id unchanged but transcript truncated — invalidate per-turn caches).
        中文 —
        在 resume/branch/reset/new 与压缩时触发。缓存按会话状态的 provider 应刷新它，使写入落到正确记录。
        参数：new_session_id；parent_session_id（branch/resume/压缩的血缘）；reset（确为新会话——清空按会话缓冲）；
            rewound（id 不变但记录被截断——失效按回合缓存）。
        """

    def on_pre_compress(self, messages: List[Dict[str, Any]]) -> str:
        """Before context compression discards old messages (ported default).

        EN: Args: messages (about to be summarized/discarded). Returns: facts to keep
            in the summary, or ``""``. The real wiring (capturing this) is §1.6.
        中文：参数：messages（即将被摘要/丢弃）。返回：应在摘要中保留的事实，或 ``""``。真正接线（捕获此值）在 §1.6。
        """
        return ""

    def on_delegation(self, task: str, result: str, *, child_session_id: str = "", **kwargs) -> None:
        """A subagent completed — parent-side observation (ported default: no-op).

        EN: Args: task (delegation prompt); result (subagent reply); child_session_id.
            The subagent has no provider session (skip_memory); the parent adjudicates writes.
        中文：参数：task（委派提示）；result（子代理答复）；child_session_id。
            子代理无 provider 会话（skip_memory）；由父代理审定写入。
        """

    def get_config_schema(self) -> List[Dict[str, Any]]:
        """Config fields this provider needs for setup (ported default: none).

        EN: Returns: a list of field dicts (key/description/secret/required/...), or ``[]``.
        中文：返回：字段字典列表（key/description/secret/required/...），或 ``[]``。
        """
        return []

    def save_config(self, values: Dict[str, Any], hermes_home: str) -> None:
        """Write non-secret config to the provider's native location (ported default: no-op).

        EN: Args: values (non-secret fields); hermes_home (the active home dir).
        中文：参数：values（非机密字段）；hermes_home（当前 home 目录）。
        """

    def on_memory_write(
        self,
        action: str,
        target: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Mirror a built-in memory write to an external backend (ported default: no-op).

        EN: Args: action ('add'/'replace'/'remove'); target; content; metadata (provenance).
            Relevant only with an external provider (Phase 2); skipped for the builtin itself.
        中文：参数：action（'add'/'replace'/'remove'）；target；content；metadata（来源）。
            仅在有外部 provider 时相关（第二阶段）；内置 provider 自身跳过。
        """

    def backup_paths(self) -> List[str]:
        """Extra on-disk paths to include in a backup (ported default: none).

        EN: Returns: absolute path strings the backup tool must also capture, or ``[]``.
            Must work without ``initialize`` and without network (resolve from config/env).
        中文：返回：备份工具还需捕获的绝对路径字符串，或 ``[]``。必须无需 ``initialize`` 与网络即可工作（由配置/环境解析）。
        """
        return []
