"""Runtime configuration — read from the environment, never from disk.

EN —
Centralises the few knobs the core needs. Secrets (the OpenAI API key) come from
the environment only; they are never written to a file or committed. ``from_env``
is the single place that reads ``os.environ``, which keeps the rest of the code
testable (construct ``CoreConfig(...)`` directly in tests). Note: in §1.1 there is
no composition root yet, so ``db_path`` / ``max_tool_iterations`` are defined here
but only wired up when the first real app entry point is added.

中文 —
集中管理内核所需的少量开关。机密（OpenAI API 密钥）仅来自环境，绝不写入文件或提交。``from_env`` 是读取
``os.environ`` 的唯一入口，使其余代码可测（测试中可直接构造 ``CoreConfig(...)``）。注意：§1.1 尚无组合根，
故 ``db_path`` / ``max_tool_iterations`` 在此定义，但要到加入首个真实应用入口时才接线。
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class CoreConfig:
    """Core runtime settings.

    EN —
    Attributes:
        openai_api_key: The OpenAI key, or ``None`` (then the OpenAI integration
            test skips and the real adapter cannot run).
        model_id: Default model id for the OpenAI adapter.
        db_path: SQLite session-store path (``:memory:`` is valid for tests).
        max_tool_iterations: Max tool rounds per turn before the loop stops.

    中文 —
    属性：
        openai_api_key：OpenAI 密钥，或 ``None``（此时 OpenAI 集成测试跳过，真实适配器无法运行）。
        model_id：OpenAI 适配器的默认模型 id。
        db_path：SQLite 会话存储路径（测试可用 ``:memory:``）。
        max_tool_iterations：每回合在循环停止前的最大工具轮数。
    """

    openai_api_key: str | None = None
    model_id: str = "gpt-4o-mini"
    db_path: str = "jobpin_sessions.db"
    max_tool_iterations: int = 8

    @classmethod
    def from_env(cls) -> "CoreConfig":
        """Build a config from environment variables.

        EN —
        Reads ``OPENAI_API_KEY``, ``JOBPIN_MODEL_ID``, ``JOBPIN_DB_PATH`` and
        ``JOBPIN_MAX_TOOL_ITERS`` (the last three falling back to the dataclass
        defaults).
        Returns:
            A populated ``CoreConfig``.

        中文 —
        读取 ``OPENAI_API_KEY``、``JOBPIN_MODEL_ID``、``JOBPIN_DB_PATH`` 与
        ``JOBPIN_MAX_TOOL_ITERS``（后三者回退到 dataclass 默认值）。
        返回：
            已填充的 ``CoreConfig``。
        """
        return cls(
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            model_id=os.environ.get("JOBPIN_MODEL_ID", "gpt-4o-mini"),
            db_path=os.environ.get("JOBPIN_DB_PATH", "jobpin_sessions.db"),
            max_tool_iterations=int(os.environ.get("JOBPIN_MAX_TOOL_ITERS", "8")),
        )
