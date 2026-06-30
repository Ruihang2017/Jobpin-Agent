"""Runtime configuration — read from the environment (optionally via a .env file).

EN —
Centralises the few knobs the core needs. Secrets (the OpenAI API key) are read
from the environment; for local development ``from_env`` first loads a gitignored
``.env`` file if present (without overriding variables already set in the real
environment), so you can keep your key in ``agent/.env`` instead of exporting it
in every shell. We never *write* secrets to disk. ``from_env`` is the single place
that reads ``os.environ``, which keeps the rest of the code testable. Note: §1.1
has no composition root yet, so ``db_path`` / ``max_tool_iterations`` are defined
here but only wired up when the first real app entry point is added.

中文 —
集中管理内核所需的少量开关。机密（OpenAI API 密钥）从环境读取；本地开发时 ``from_env`` 会先加载（若存在）一个被
gitignore 的 ``.env`` 文件（不覆盖真实环境中已设置的变量），因此你可以把密钥放在 ``agent/.env`` 而不必每个 shell
都导出。我们绝不把机密*写入*磁盘。``from_env`` 是读取 ``os.environ`` 的唯一入口，使其余代码可测。注意：§1.1 尚无
组合根，故 ``db_path`` / ``max_tool_iterations`` 在此定义，但要到加入首个真实应用入口时才接线。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv(path: Path | None = None) -> None:
    """Seed ``os.environ`` from a ``.env`` file (without overriding existing vars).

    EN —
    Loads simple ``KEY=VALUE`` lines (``#`` comments and blank lines ignored;
    surrounding single/double quotes stripped). Existing environment variables win
    (via ``os.environ.setdefault``), so an explicitly-exported value is never
    clobbered. Only the first existing candidate file is loaded.
    Args:
        path: An explicit ``.env`` path (used in tests). When ``None``, the first
            existing file among ``cwd/.env``, ``agent/.env`` and ``<repo>/.env`` is
            used.

    中文 —
    加载简单的 ``KEY=VALUE`` 行（忽略 ``#`` 注释与空行；去除首尾单/双引号）。已存在的环境变量优先
    （经 ``os.environ.setdefault``），故显式导出的值绝不会被覆盖。仅加载第一个存在的候选文件。
    参数：
        path：显式的 ``.env`` 路径（测试用）。为 ``None`` 时，使用 ``cwd/.env``、``agent/.env`` 与
            ``<repo>/.env`` 中第一个存在的文件。
    """
    here = Path(__file__).resolve()
    candidates = [path] if path is not None else [
        Path.cwd() / ".env",
        here.parents[3] / ".env",   # agent/.env
        here.parents[4] / ".env",   # <repo root>/.env
    ]
    for candidate in candidates:
        if candidate and candidate.is_file():
            for raw in candidate.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
            return


@dataclass
class CoreConfig:
    """Core runtime settings.

    EN —
    Attributes:
        openai_api_key: The OpenAI key (from the environment or ``.env``), or
            ``None`` (then the OpenAI integration test skips and the real adapter
            cannot run).
        model_id: Default model id for the OpenAI adapter.
        db_path: SQLite session-store path (``:memory:`` is valid for tests).
        max_tool_iterations: Max tool rounds per turn before the loop stops.
        encryption_enabled: When True, local stores are opened with at-rest encryption (§1.9); the
            master key is taken from the OS keystore at ``master_key_path``. Default False keeps the
            existing test suite and demos unchanged (plain SQLite, plaintext files).
        master_key_path: Path to the OS-keystore-protected master-key file (§1.9 ``KeyStore``).

    中文 —
    属性：
        openai_api_key：OpenAI 密钥（来自环境或 ``.env``），或 ``None``（此时 OpenAI 集成测试跳过，真实适配器
            无法运行）。
        model_id：OpenAI 适配器的默认模型 id。
        db_path：SQLite 会话存储路径（测试可用 ``:memory:``）。
        max_tool_iterations：每回合在循环停止前的最大工具轮数。
        encryption_enabled：为 True 时，本地存储以静态加密打开（§1.9）；主密钥取自 ``master_key_path`` 处的 OS
            keystore。默认 False，使既有测试套件与演示保持不变（普通 SQLite、明文文件）。
        master_key_path：受 OS keystore 保护的主密钥文件路径（§1.9 ``KeyStore``）。
    """

    openai_api_key: str | None = None
    model_id: str = "gpt-4o-mini"
    db_path: str = "jobpin_sessions.db"
    max_tool_iterations: int = 8
    encryption_enabled: bool = False
    master_key_path: str = "jobpin_master.key"

    @classmethod
    def from_env(cls) -> "CoreConfig":
        """Build a config from environment variables (seeding from ``.env`` first).

        EN —
        First calls ``_load_dotenv()`` so a local ``.env`` (e.g. ``agent/.env``)
        populates any unset variables, then reads ``OPENAI_API_KEY``,
        ``JOBPIN_MODEL_ID``, ``JOBPIN_DB_PATH``, ``JOBPIN_MAX_TOOL_ITERS``,
        ``JOBPIN_ENCRYPTION`` (``"1"`` enables at-rest encryption) and
        ``JOBPIN_KEY_PATH`` (all falling back to the dataclass defaults).
        Returns:
            A populated ``CoreConfig``.

        中文 —
        先调用 ``_load_dotenv()``，使本地 ``.env``（如 ``agent/.env``）填充任何未设置的变量，然后读取
        ``OPENAI_API_KEY``、``JOBPIN_MODEL_ID``、``JOBPIN_DB_PATH``、``JOBPIN_MAX_TOOL_ITERS``、
        ``JOBPIN_ENCRYPTION``（``"1"`` 启用静态加密）与 ``JOBPIN_KEY_PATH``（均回退到 dataclass 默认值）。
        返回：
            已填充的 ``CoreConfig``。
        """
        _load_dotenv()
        return cls(
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            model_id=os.environ.get("JOBPIN_MODEL_ID", "gpt-4o-mini"),
            db_path=os.environ.get("JOBPIN_DB_PATH", "jobpin_sessions.db"),
            max_tool_iterations=int(os.environ.get("JOBPIN_MAX_TOOL_ITERS", "8")),
            encryption_enabled=os.environ.get("JOBPIN_ENCRYPTION", "") == "1",
            master_key_path=os.environ.get("JOBPIN_KEY_PATH", "jobpin_master.key"),
        )
