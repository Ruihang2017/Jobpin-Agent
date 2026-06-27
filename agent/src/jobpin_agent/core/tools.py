"""Tool registry — how the agent exposes callable tools to the model.

EN —
A tool is a named function with a JSON-schema description and a Python handler.
The registry holds the tools the agent may use, advertises them to the model
(via the system prompt and the provider's tool list), and executes a tool when
the model asks for it. In §1.1 the only tool is ``echo``, used to exercise the
tool-call path; real HR tools and MCP connectors arrive in later points.

中文 —
工具是带 JSON-schema 描述与 Python 处理函数的具名函数。注册表持有 agent 可用的工具、把它们告知
模型（经系统提示与提供商的工具列表），并在模型请求时执行。§1.1 仅有 ``echo`` 工具，用于演练工具调用
路径；真正的 HR 工具与 MCP 连接器在后续节点引入。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .messages import ToolCall, ToolResult


@dataclass
class ToolSpec:
    """The definition of one tool.

    EN —
    Attributes:
        name: Unique tool name the model uses to call it.
        description: One-line purpose, shown to the model in the system prompt.
        parameters: JSON-schema object describing the accepted arguments.
        handler: Callable taking the parsed arguments dict and returning a string.

    中文 —
    属性：
        name：模型调用时使用的唯一工具名。
        description：一行用途说明，经系统提示展示给模型。
        parameters：描述可接受参数的 JSON-schema 对象。
        handler：接收解析后参数 dict 并返回字符串的可调用对象。
    """

    name: str
    description: str
    parameters: dict  # JSON schema
    handler: Callable[[dict], str]


class ToolRegistry:
    """A collection of tools the agent can advertise and execute.

    EN —
    Holds tools by name. ``specs()`` is consumed by the system-prompt assembler
    and the provider to tell the model what is available; ``execute()`` runs the
    handler for a model-requested ``ToolCall``.

    中文 —
    按名持有工具。``specs()`` 供系统提示装配器与提供商使用，以告知模型可用工具；``execute()``
    针对模型请求的 ``ToolCall`` 运行对应处理函数。
    """

    def __init__(self) -> None:
        """Create an empty registry.

        EN: Initialises the internal name→spec mapping.
        中文：初始化内部的 名称→规格 映射。
        """
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        """Add (or replace) a tool.

        EN —
        Args:
            spec: The tool definition; an existing tool with the same name is overwritten.

        中文 —
        参数：
            spec：工具定义；同名的已有工具将被覆盖。
        """
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec:
        """Look up a tool by name.

        EN —
        Args:
            name: The tool name.
        Returns:
            The matching ``ToolSpec``.
        Raises:
            KeyError: If no tool with that name is registered.

        中文 —
        参数：
            name：工具名。
        返回：
            匹配的 ``ToolSpec``。
        抛出：
            KeyError：若未注册该名称的工具。
        """
        if name not in self._tools:
            raise KeyError(f"unknown tool: {name}")
        return self._tools[name]

    def specs(self) -> list[ToolSpec]:
        """List all registered tools.

        EN —
        Returns:
            A new list of the registered ``ToolSpec`` objects.

        中文 —
        返回：
            已注册 ``ToolSpec`` 对象的新列表。
        """
        return list(self._tools.values())

    def execute(self, call: ToolCall) -> ToolResult:
        """Run the handler for a model-requested tool call.

        EN —
        Args:
            call: The ``ToolCall`` produced by the model (already-parsed arguments).
        Returns:
            A ``ToolResult`` correlated to ``call.id``, carrying the handler output.
        Raises:
            KeyError: If ``call.name`` is not registered.

        中文 —
        参数：
            call：模型产出的 ``ToolCall``（参数已解析）。
        返回：
            与 ``call.id`` 关联、携带处理函数输出的 ``ToolResult``。
        抛出：
            KeyError：若 ``call.name`` 未注册。
        """
        spec = self.get(call.name)
        content = spec.handler(call.arguments)
        return ToolResult(tool_call_id=call.id, name=call.name, content=content)


def echo_tool() -> ToolSpec:
    """Build the trivial ``echo`` demo tool.

    EN —
    A minimal tool that returns its ``text`` argument unchanged. It exists only
    to exercise the tool-call path in §1.1 (and the demo/tests).
    Returns:
        A ready-to-register ``ToolSpec`` named ``"echo"``.

    中文 —
    一个最小工具，原样返回其 ``text`` 参数。仅用于在 §1.1 演练工具调用路径（以及演示/测试）。
    返回：
        可直接注册、名为 ``"echo"`` 的 ``ToolSpec``。
    """
    return ToolSpec(
        name="echo",
        description="Echo back the provided text.",
        parameters={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
        handler=lambda args: str(args.get("text", "")),
    )
