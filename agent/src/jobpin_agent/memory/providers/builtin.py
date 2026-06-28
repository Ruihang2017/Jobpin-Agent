"""The built-in memory provider — wraps the §1.2 file-backed ``MemoryStore``.

EN —
Makes the curated Org/Recruiter store (§1.2) participate in the ``MemoryProvider``
lifecycle so the Manager can orchestrate it alongside future entity providers
(§1.4), and so file-backed memory gets the ``on_pre_compress`` seam the §1.6
pre-compression wiring needs ("MemoryStore is not a Provider" gap, Plan §1.6).

§1.3 keeps it deliberately lean (read/seam path only):
- The curated frozen snapshot reaches the system prompt DIRECTLY via the §1.1
  ``memory_snapshot`` slot (assembly order, Plan §1.1), so ``system_prompt_block``
  returns ``""`` here — returning the snapshot would duplicate it.
- ``prefetch`` returns ``""`` (curated memory is static in the prompt; per-query
  recall is §1.4's vector providers).
- ``sync_turn`` is a no-op (curated memory is hand-edited, not auto-written per
  turn; the governed ``memory`` write tool is §1.5).
- ``get_tool_schemas`` returns ``[]`` (the write tool is §1.5).

中文 —
让策展的 Org/Recruiter 存储（§1.2）参与 ``MemoryProvider`` 生命周期，使 Manager 能与未来的实体 provider
（§1.4）一同编排它，并让文件型记忆获得 §1.6 压缩前接线所需的 ``on_pre_compress`` 接缝（“MemoryStore 不是
Provider”的缺口，计划 §1.6）。

§1.3 刻意保持精简（仅读/接缝路径）：
- 策展的冻结快照经 §1.1 ``memory_snapshot`` 槽位直接进入系统提示（装配顺序，计划 §1.1），故此处
  ``system_prompt_block`` 返回 ``""``——返回快照会造成重复。
- ``prefetch`` 返回 ``""``（策展记忆在提示中是静态的；按查询召回是 §1.4 的向量 provider）。
- ``sync_turn`` 为空操作（策展记忆是人工编辑，而非每回合自动写入；受治理的 ``memory`` 写工具在 §1.5）。
- ``get_tool_schemas`` 返回 ``[]``（写工具在 §1.5）。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..provider import MemoryProvider
from ..store import MemoryStore


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

    def __init__(self, store: MemoryStore) -> None:
        """Wrap a loaded ``MemoryStore``.

        EN: Args: store — a §1.2 store (already ``load_from_disk()``-ed by the composition root).
        中文：参数：store——§1.2 存储（已由组合根 ``load_from_disk()``）。
        """
        self._store = store

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
        """No-op: the store is loaded by the composition root before use.

        EN: Args: session_id; kwargs (ignored). Returns: None.
        中文：参数：session_id；kwargs（忽略）。返回：None。
        """
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
        """No tools yet — the governed ``memory`` write tool lands at §1.5.

        EN: Returns: ``[]``.
        中文：返回：``[]``。
        """
        return []

    def on_pre_compress(self, messages: List[Dict[str, Any]]) -> str:
        """Seam for §1.6: the file store can take part in pre-compression extraction.

        EN: Args: messages (ignored in §1.3). Returns: ``""`` (real extraction is §1.6).
        中文：参数：messages（§1.3 忽略）。返回：``""``（真实抽取在 §1.6）。
        """
        return ""

    def shutdown(self) -> None:
        """No-op (no resources held).

        EN: Returns: None.
        中文：返回：None。
        """
        return None
