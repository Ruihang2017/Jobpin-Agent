# `agent/examples/` — runnable examples

## English
Scripts that demonstrate the core end-to-end.

- `demo_turn.py` — **offline** smoke demo. Uses the scripted `FakeProvider` (no key,
  no network), so it always prints the same canned result. Run:
  `python agent/examples/demo_turn.py`.
- `chat.py` — **real** interactive chat. Uses your OpenAI key (from `agent/.env`)
  and `OpenAIProvider`; type messages and get real replies, with the `echo` tool.
  Each turn prints a step + token summary and writes a full JSONL trace to
  `agent/traces/latest.jsonl`; `/trace` dumps every step's prompt/response/tool
  IO/latency/tokens. Run: `python agent/examples/chat.py` (commands: `/exit`,
  `/trace`, `/reset`).

## 中文
演示内核端到端的脚本。

- `demo_turn.py` — **离线**冒烟演示。使用脚本化 `FakeProvider`（无密钥、无网络），故始终打印相同的预设结果。运行：
  `python agent/examples/demo_turn.py`。
- `chat.py` — **真实**交互式聊天。使用你的 OpenAI 密钥（来自 `agent/.env`）与 `OpenAIProvider`；输入消息即可获得
  真实答复，含每回合步骤追踪与 `echo` 工具。运行：`python agent/examples/chat.py`（命令：`/exit`、`/trace`、
  `/reset`）。
