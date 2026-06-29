"""Registry to manager bridge — expose the governed ``memory`` tool with no loop change (§1.5).

EN —
The §1.1 agent loop dispatches tools through ``core.tools.ToolRegistry`` only; the memory subsystem
attaches via the ``MemoryHooks`` seam (recall/sync), not the tool path. To make the governed ``memory``
write tool model-callable WITHOUT touching ``agent_loop.py`` (Key Invariant, held across §1.2–slice),
the composition root registers this ``ToolSpec`` into the ``ToolRegistry``. Its handler routes the call
to ``MemoryManager.handle_tool_call`` (→ the builtin provider's governed write) and then mirrors a
committed write to any external provider via the manager's already-ported ``notify_memory_tool_write``.

中文 —
§1.1 agent 循环只经 ``core.tools.ToolRegistry`` 派发工具；记忆子系统经 ``MemoryHooks`` 接缝（召回/同步）接入，而非
工具路径。为在**不改动 ``agent_loop.py``**（关键不变量，自 §1.2–切片保持）的前提下使受治理的 ``memory`` 写工具可被
模型调用，组合根把此 ``ToolSpec`` 注册进 ``ToolRegistry``。其处理函数将调用路由到 ``MemoryManager.handle_tool_call``
（→ 内置 provider 的受治理写入），随后经 manager 已移植的 ``notify_memory_tool_write`` 把已提交写入镜像给任何外部
provider。
"""
from __future__ import annotations

from ..core.tools import ToolSpec
from ..memory.manager import MemoryManager
from ..memory.providers.builtin import MEMORY_TOOL_SCHEMA


def build_memory_tool(manager: MemoryManager) -> ToolSpec:
    """Build the ``memory`` ``ToolSpec`` bridging the registry to the manager (governed write + mirror).

    EN —
    Args: manager — a ``MemoryManager`` whose builtin provider has a §1.5 gate. Returns: a ``ToolSpec``
    named ``"memory"`` to register in the agent's ``ToolRegistry``; its handler runs the governed write
    and mirrors a committed write to external providers.

    中文 —
    参数：manager——其内置 provider 带 §1.5 门控的 ``MemoryManager``。返回：名为 ``"memory"`` 的 ``ToolSpec``，注册进
    agent 的 ``ToolRegistry``；其处理函数执行受治理写入，并把已提交写入镜像给外部 provider。
    """
    def handler(args: dict) -> str:
        result = manager.handle_tool_call("memory", args)
        manager.notify_memory_tool_write(result, args)
        return result

    return ToolSpec(
        name="memory",
        description=MEMORY_TOOL_SCHEMA["description"],
        parameters=MEMORY_TOOL_SCHEMA["parameters"],
        handler=handler,
    )
