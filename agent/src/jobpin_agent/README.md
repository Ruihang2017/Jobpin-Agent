# `jobpin_agent/` — the product package

## English
The importable Python package for the Jobpin Agent product. Today it contains the
Agent Core (Layer A); later Production-Plan points add memory, governance,
orchestration, integration, and the AI/eval platform as sibling subpackages.

- `__init__.py` — package marker; exposes `__version__`.
- `core/` — Agent Core (Layer A): the conversation loop, system prompt, tools,
  session store, model layer, tracing, and the memory-hooks seam (§1.1).
- `memory/` — Memory Subsystem (§1.2–1.4): the file-backed curated store, the
  provider interface + manager + hooks seam, the embedded vector store, and the
  entity/semantic/composite providers.
- `governance/` — HR memory governance (§1.5): namespace, provenance/consent
  labels, the governed write-gate + memory tool, RBAC recall filter, retention,
  erasure, and the append-only audit log.
- `security/` — context-window security (§1.6): the ported threat-pattern library
  + streaming scrubber + the external-text scan/fence door. (Compression wiring
  lives in `core/compression.py`.)

Planned siblings (later points): `orchestration/`, `data/`, `integration/`,
`ai/`, `eval/`, `obs/`.

## 中文
Jobpin Agent 产品的可导入 Python 包。目前包含 Agent 内核（Layer A）；后续生产计划节点将以同级子包形式加入记忆、
治理、编排、集成与 AI/eval 平台。

- `__init__.py` — 包标记；暴露 `__version__`。
- `core/` — Agent 内核（Layer A）：会话循环、系统提示、工具、会话存储、模型层、追踪，以及记忆钩子接缝（§1.1）。
- `memory/` — 记忆子系统（§1.2–1.4）：文件型策展存储、provider 接口 + manager + hooks 接缝、嵌入式向量库，
  以及实体/语义/复合 provider。
- `governance/` — HR 记忆治理（§1.5）：命名空间、来源/同意标签、受治理写门控 + 记忆工具、RBAC 召回过滤、留存、
  擦除，以及仅追加审计日志。
- `security/` — 上下文窗口安全（§1.6）：移植的威胁模式库 + 流式清洗器 + 外部文本扫描/围栏入口。
  （压缩接线位于 `core/compression.py`。）

规划中的同级目录（后续节点）：`orchestration/`、`data/`、`integration/`、`ai/`、`eval/`、`obs/`。
