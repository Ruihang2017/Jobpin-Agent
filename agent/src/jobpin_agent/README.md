# `jobpin_agent/` — the product package

## English
The importable Python package for the Jobpin Agent product. Today it contains the
Agent Core (Layer A); later Production-Plan points add memory, governance,
orchestration, integration, and the AI/eval platform as sibling subpackages.

- `__init__.py` — package marker; exposes `__version__`.
- `core/` — Agent Core (Layer A): the conversation loop, system prompt, tools,
  session store, model layer, tracing, and the memory-hooks seam (§1.1).

Planned siblings (later points): `memory/`, `governance/`, `security/`,
`orchestration/`, `data/`, `integration/`, `ai/`, `eval/`, `obs/`.

## 中文
Jobpin Agent 产品的可导入 Python 包。目前包含 Agent 内核（Layer A）；后续生产计划节点将以同级子包形式加入记忆、
治理、编排、集成与 AI/eval 平台。

- `__init__.py` — 包标记；暴露 `__version__`。
- `core/` — Agent 内核（Layer A）：会话循环、系统提示、工具、会话存储、模型层、追踪，以及记忆钩子接缝（§1.1）。

规划中的同级目录（后续节点）：`memory/`、`governance/`、`security/`、`orchestration/`、`data/`、`integration/`、
`ai/`、`eval/`、`obs/`。
