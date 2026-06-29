"""Tests for the MemoryProvider ABC and the built-in provider (§1.3).

EN — The ABC enforces its abstract members; the built-in provider is the lean
read/seam wrapper over the §1.2 store (snapshot goes via the memory_snapshot slot).
中文 — ABC 强制其抽象成员；内置 provider 是 §1.2 存储之上的精简读/接缝包装（快照经 memory_snapshot 槽位）。
"""
import pytest

from jobpin_agent.memory.provider import MemoryProvider
from jobpin_agent.memory.providers.builtin import BuiltinMemoryProvider
from jobpin_agent.memory.store import MemoryStore


class _Min(MemoryProvider):
    """A minimal concrete provider implementing only the abstract members.

    EN — Used to prove the ABC's optional-hook defaults. 中文 — 用于验证 ABC 可选钩子的默认实现。
    """

    @property
    def name(self) -> str:
        """EN: Returns 'min'. 中文：返回 'min'。"""
        return "min"

    def is_available(self) -> bool:
        """EN: Returns True. 中文：返回 True。"""
        return True

    def initialize(self, session_id, **kwargs):
        """EN: No-op. 中文：空操作。"""
        return None

    def get_tool_schemas(self):
        """EN: Returns []. 中文：返回 []。"""
        return []


def test_cannot_instantiate_without_abstracts():
    """The ABC cannot be instantiated directly (abstract members unimplemented).

    EN: instantiating MemoryProvider raises TypeError. 中文：实例化 MemoryProvider 抛 TypeError。
    """
    with pytest.raises(TypeError):
        MemoryProvider()  # type: ignore[abstract]


def test_minimal_provider_defaults():
    """The opt-in hooks return Hermes's defaults on a minimal provider.

    EN: system_prompt_block/prefetch/on_pre_compress -> ""; sync_turn -> None; backup_paths -> [].
    中文：system_prompt_block/prefetch/on_pre_compress -> ""；sync_turn -> None；backup_paths -> []。
    """
    p = _Min()
    assert p.name == "min" and p.is_available() is True
    assert p.system_prompt_block() == "" and p.prefetch("q") == "" and p.on_pre_compress([]) == ""
    assert p.sync_turn("u", "a") is None and p.backup_paths() == [] and p.get_config_schema() == []


def test_builtin_provider_is_lean_seam(tmp_path):
    """The built-in provider wraps the store but stays lean in §1.3.

    EN: name builtin; system_prompt_block/prefetch/on_pre_compress -> ""; no tools; sync_turn no-op.
    中文：name 为 builtin；system_prompt_block/prefetch/on_pre_compress -> ""；无工具；sync_turn 空操作。
    """
    (tmp_path / "ORG.md").write_text("Hire for impact.", encoding="utf-8")
    store = MemoryStore(tmp_path)
    store.load_from_disk()
    p = BuiltinMemoryProvider(store)
    assert p.name == "builtin" and p.is_available() is True
    assert p.system_prompt_block() == ""  # snapshot goes via the memory_snapshot slot, not here
    assert p.prefetch("anything") == "" and p.get_tool_schemas() == []
    assert p.sync_turn("u", "a") is None and p.on_pre_compress([]) == ""
    assert p.store.format_for_system_prompt("org") is not None  # the store still holds the snapshot
