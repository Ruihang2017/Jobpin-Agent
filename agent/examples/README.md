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
- `memory_inspect.py` — **offline** §1.2 demo. Adds Org/Recruiter entries to a temp
  `MemoryStore`, prints the frozen system-prompt snapshot, and shows drift rejection.
- `memory_agent_demo.py` — **offline** §1.3 demo. Wires the `MemoryManager` + hooks to a
  §1.1 `Agent` (fake model) and shows the Org snapshot + a fenced `<memory-context>` recall
  reaching the prompt, with the turn syncing — no `agent_loop.py` change.
- `recall_demo.py` — **offline** §1.4 demo. Résumé → vectorize → the right candidate (with a
  `[memory_key | source]` citation) reaches a §1.1 `Agent` (fake model) through the Composite.
- `hiring_slice_demo.py` — the **hiring vertical slice**. Ingests synthetic résumés + an org
  rubric and asks a hiring question; the agent recalls the fitting candidates and returns an
  explainable, cited, **HITL-framed** shortlist. Uses a **real** OpenAI model + embeddings when
  `OPENAI_API_KEY` is set (`agent/.env`), else the offline fake model + lexical embedder.
  Synthetic résumés only. Run: `python agent/examples/hiring_slice_demo.py`.

## 中文
演示内核端到端的脚本。

- `demo_turn.py` — **离线**冒烟演示。使用脚本化 `FakeProvider`（无密钥、无网络），故始终打印相同的预设结果。运行：
  `python agent/examples/demo_turn.py`。
- `chat.py` — **真实**交互式聊天。使用你的 OpenAI 密钥（来自 `agent/.env`）与 `OpenAIProvider`；输入消息即可获得
  真实答复，含每回合步骤追踪与 `echo` 工具。运行：`python agent/examples/chat.py`（命令：`/exit`、`/trace`、
  `/reset`）。
- `memory_inspect.py` — **离线** §1.2 演示。向临时 `MemoryStore` 添加 Org/Recruiter 条目，打印冻结的系统提示快照，并展示漂移拒写。
- `memory_agent_demo.py` — **离线** §1.3 演示。把 `MemoryManager` + hooks 接到 §1.1 `Agent`（fake 模型），展示 Org 快照
  与围栏 `<memory-context>` 召回到达提示、且回合完成同步——不改动 `agent_loop.py`。
- `recall_demo.py` — **离线** §1.4 演示。简历 → 向量化 → 正确候选人（带 `[memory_key | source]` 引用）经 Composite
  到达 §1.1 `Agent`（fake 模型）。
- `hiring_slice_demo.py` — **招聘垂直切片**。ingest 合成简历 + 组织评分细则并提出招聘问题；agent 召回合适候选人并返回
  可解释、带引用、**HITL 框定**的候选名单。设置 `OPENAI_API_KEY`（`agent/.env`）时用**真实** OpenAI 模型 + 嵌入，
  否则用离线 fake 模型 + 词面嵌入器。仅合成简历。运行：`python agent/examples/hiring_slice_demo.py`。
