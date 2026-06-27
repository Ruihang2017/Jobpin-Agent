# `agent/examples/` — runnable examples

## English
Self-contained scripts that demonstrate the core end-to-end. They default to the
offline `FakeProvider`, so they run deterministically with no API key.

- `demo_turn.py` — runs a plain turn, a tool-call turn, and a delegation, and
  prints a result summary. Run: `python agent/examples/demo_turn.py`.

## 中文
演示内核端到端的自包含脚本。默认使用离线 `FakeProvider`，无需 API 密钥即可确定性运行。

- `demo_turn.py` — 运行一个纯文本回合、一个工具调用回合与一次委派，并打印结果摘要。运行：
  `python agent/examples/demo_turn.py`。
