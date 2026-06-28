"""Compose the memory backend and wire it to the §1.1 system-prompt slots.

EN —
``build_memory_backend`` assembles the Memory Subsystem for §1.3: load the §1.2
``MemoryStore``, wrap it in the built-in provider, register it (plus any extra
providers) on a ``MemoryManager``, and expose a ``MemoryManagerHooks`` adapter. The
returned ``MemoryBackend`` also produces the two system-prompt fills the §1.1
assembler expects (Plan §1.1 order): ``memory_snapshot()`` (the store's frozen
Org+Recruiter block, straight from the store) and ``provider_block()``
(``manager.build_system_prompt()``). This is the memory-subsystem assembly helper —
NOT the application entry point (a real composition root arrives with the app).

中文 —
``build_memory_backend`` 为 §1.3 装配记忆子系统：加载 §1.2 ``MemoryStore``、用内置 provider 包裹、注册到
``MemoryManager``（外加任意额外 provider），并暴露 ``MemoryManagerHooks`` 适配器。返回的 ``MemoryBackend`` 还产出
§1.1 装配器所需的两处系统提示填充（计划 §1.1 顺序）：``memory_snapshot()``（存储的冻结 Org+Recruiter 块，直接取自
存储）与 ``provider_block()``（``manager.build_system_prompt()``）。这是记忆子系统装配助手——并非应用入口
（真正的组合根随应用到来）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Optional

from .manager import MemoryManager
from .manager_hooks import MemoryManagerHooks
from .provider import MemoryProvider
from .providers.builtin import BuiltinMemoryProvider
from .store import MemoryStore, load_org_recruiter_store


@dataclass
class MemoryBackend:
    """The assembled memory backend (store + manager + seam adapter).

    EN —
    Attributes: store (§1.2); manager (§1.3 orchestrator); hooks (the §1.1
    ``MemoryHooks`` adapter to pass as ``Agent(..., hooks=...)``).

    中文 —
    属性：store（§1.2）；manager（§1.3 编排器）；hooks（作为 ``Agent(..., hooks=...)`` 传入的 §1.1
    ``MemoryHooks`` 适配器）。
    """

    store: MemoryStore
    manager: MemoryManager
    hooks: MemoryManagerHooks

    def memory_snapshot(self) -> str:
        """The frozen Org+Recruiter snapshot for the §1.1 ``memory_snapshot`` slot.

        EN: Returns: the two non-empty blocks joined by a blank line (or ``""``). Taken
            straight from the store (Plan §1.1 assembly order), not the provider block.
        中文：返回：两个非空块以空行连接（或 ``""``）。直接取自存储（计划 §1.1 装配顺序），而非 provider 块。
        """
        blocks = [self.store.format_for_system_prompt(t) for t in ("org", "recruiter")]
        return "\n\n".join(b for b in blocks if b)

    def provider_block(self) -> str:
        """The providers' static blocks for the §1.1 ``provider_block`` slot.

        EN: Returns: ``manager.build_system_prompt()`` (empty for builtin-only in §1.3).
        中文：返回：``manager.build_system_prompt()``（§1.3 仅 builtin 时为空）。
        """
        return self.manager.build_system_prompt()


def build_memory_backend(
    memory_dir,
    *,
    extra_providers: Iterable[MemoryProvider] = (),
    scan_entry: Optional[Callable[[str], Optional[str]]] = None,
    write_gate=None,
) -> MemoryBackend:
    """Assemble store + builtin provider + manager + hooks for ``memory_dir``.

    EN —
    Args:
        memory_dir: directory holding ORG.md / RECRUITER.md (created/loaded by §1.2).
        extra_providers: additional providers to register (e.g. a §1.4 recall
            provider, or a fake in tests); the single-external rule still applies.
        scan_entry / write_gate: passed through to the §1.2 store (threat-scan seam §1.6 /
            write-approval seam §1.5).
    Returns: a ``MemoryBackend``.

    Note: this only assembles wiring — it does NOT drive the per-session lifecycle
    (``manager.initialize_all`` / ``shutdown_all``). That is the caller's job and matters
    once §1.4 adds real ``extra_providers`` with resources; the §1.3 builtin's init/shutdown
    are no-ops, so omitting it here is harmless.

    中文 —
    参数：
        memory_dir：存放 ORG.md / RECRUITER.md 的目录（由 §1.2 创建/加载）。
        extra_providers：要注册的额外 provider（如 §1.4 召回 provider，或测试中的 fake）；单外部规则仍适用。
        scan_entry / write_gate：透传给 §1.2 存储（威胁扫描接缝 §1.6 / 写审批接缝 §1.5）。
    返回：``MemoryBackend``。
    """
    store = load_org_recruiter_store(memory_dir, scan_entry=scan_entry, write_gate=write_gate)
    manager = MemoryManager()
    manager.add_provider(BuiltinMemoryProvider(store))
    for provider in extra_providers:
        manager.add_provider(provider)
    return MemoryBackend(store=store, manager=manager, hooks=MemoryManagerHooks(manager))
