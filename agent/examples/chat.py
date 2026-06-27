"""Interactive chat against a real model — uses your key from agent/.env.

EN —
A tiny REPL that wires the §1.1 Agent Core to the real ``OpenAIProvider`` and lets
you type messages and get real model replies, with the ``echo`` tool available and
a per-turn step trace printed so you can watch the loop work. Unlike
``demo_turn.py`` (offline, scripted), this one actually calls OpenAI — so it needs
a key. ``CoreConfig.from_env()`` loads ``agent/.env`` automatically.

Run from the ``agent/`` folder:
    python examples/chat.py
Commands: ``/exit`` to quit, ``/trace`` to dump all steps so far, ``/reset`` to
start a fresh session.

中文 —
一个极小的 REPL：把 §1.1 Agent 内核接到真实的 ``OpenAIProvider``，让你输入消息并获得真实模型答复，并提供
``echo`` 工具，且每回合打印步骤追踪，便于你观察循环的运作。与 ``demo_turn.py``（离线、脚本化）不同，本脚本真正
调用 OpenAI——因此需要密钥。``CoreConfig.from_env()`` 会自动加载 ``agent/.env``。

在 ``agent/`` 目录下运行：
    python examples/chat.py
命令：``/exit`` 退出，``/trace`` 打印迄今所有步骤，``/reset`` 开始新会话。
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow `python agent/examples/chat.py` without setting PYTHONPATH.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpin_agent.core.agent_loop import Agent
from jobpin_agent.core.config import CoreConfig
from jobpin_agent.core.model.openai_provider import OpenAIProvider
from jobpin_agent.core.session_store import SessionStore
from jobpin_agent.core.tools import ToolRegistry, echo_tool
from jobpin_agent.core.tracing import Tracer


def main() -> None:
    """Run the interactive chat loop against OpenAI until the user exits.

    EN —
    Loads config (incl. ``agent/.env``); if no key is found, prints how to set one
    and exits. Otherwise builds an ``Agent`` backed by ``OpenAIProvider`` and runs
    a multi-turn REPL, printing each turn's answer and the engine steps it took.
    Returns: None.

    中文 —
    加载配置（含 ``agent/.env``）；若未找到密钥，则提示如何设置并退出。否则构建一个由 ``OpenAIProvider`` 支撑的
    ``Agent`` 并运行多回合 REPL，打印每回合的答复及其经历的引擎步骤。返回：None。
    """
    config = CoreConfig.from_env()
    if not config.openai_api_key:
        print("No OPENAI_API_KEY found. Copy agent/.env.example to agent/.env and set your key, "
              "or export OPENAI_API_KEY, then rerun.")
        return

    registry = ToolRegistry()
    registry.register(echo_tool())
    store = SessionStore()
    tracer = Tracer()
    agent = Agent(OpenAIProvider(config), registry, store, tracer=tracer)
    session_id = store.create_session("chat")

    print(f"Chatting with model '{config.model_id}'. The 'echo' tool is available.")
    print("Type a message. Commands: /exit, /trace, /reset.\n")
    while True:
        try:
            user_input = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_input:
            continue
        if user_input == "/exit":
            break
        if user_input == "/trace":
            print("  all steps so far:", [e.kind for e in tracer.events])
            continue
        if user_input == "/reset":
            session_id = store.create_session()
            print("  (new session started)")
            continue

        before = len(tracer.events)
        result = agent.run_turn(session_id, user_input)
        steps = [e.kind for e in tracer.events[before:]]
        answer = result.text if not result.stopped else "[stopped: hit the tool-iteration limit]"
        print(f"agent> {answer}")
        print(f"  (steps this turn: {steps})\n")


if __name__ == "__main__":  # pragma: no cover
    main()
