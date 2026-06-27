"""Env-based config. Secrets only from the environment; never written to disk."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class CoreConfig:
    openai_api_key: str | None = None
    model_id: str = "gpt-4o-mini"
    db_path: str = "jobpin_sessions.db"
    max_tool_iterations: int = 8

    @classmethod
    def from_env(cls) -> "CoreConfig":
        return cls(
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            model_id=os.environ.get("JOBPIN_MODEL_ID", "gpt-4o-mini"),
            db_path=os.environ.get("JOBPIN_DB_PATH", "jobpin_sessions.db"),
            max_tool_iterations=int(os.environ.get("JOBPIN_MAX_TOOL_ITERS", "8")),
        )
