# Jobpin Agent (product source)

The actual Jobpin Agent product — a local-first, AI-agent HR platform.
This directory is **not** part of the Netlify-deployed docs site.

- Product requirements: `../site/plan/01-PRD-EN.md`
- Delivery roadmap: `../site/plan/02-Production-Plan-EN.md`
- Hermes porting source (read-only): `../reference/hermes/`
- License hygiene for ported code: `THIRD_PARTY_NOTICES.md`

## Dev quickstart

```bash
cd agent
python -m pytest        # runs the offline test suite (no key needed)
```

To run against a real model, copy the env template and add your OpenAI key
(`.env` is gitignored — never commit it):

```bash
cp .env.example .env    # then edit .env: OPENAI_API_KEY=sk-...
```

`CoreConfig.from_env()` loads `agent/.env` automatically. Internal structure
(Agent Core, Memory Subsystem, sub-agents, orchestration) is built in Phase 0 of
the Production Plan and intentionally not scaffolded yet.

## Contents / 目录

**English** — what's in this folder (subfolders have their own bilingual `README.md`):
- `CLAUDE.md` — scoped agent-dev guide (porting discipline, invariants, conventions).
- `pyproject.toml` — package metadata + pytest config (`pythonpath`, deps).
- `THIRD_PARTY_NOTICES.md` — MIT notices + provenance for code ported from Hermes.
- `src/jobpin_agent/` — the product package (`core/` = Agent Core today).
- `tests/` — the pytest suite (one module per source module) + `data/` fixtures.
- `examples/` — runnable demos (`demo_turn.py`).

**中文** — 本文件夹内容（子文件夹有各自的双语 `README.md`）：
- `CLAUDE.md` — 范围化的 agent 开发指南（移植纪律、不变量、约定）。
- `pyproject.toml` — 包元数据 + pytest 配置（`pythonpath`、依赖）。
- `THIRD_PARTY_NOTICES.md` — 从 Hermes 移植代码的 MIT 声明与来源。
- `src/jobpin_agent/` — 产品包（当前 `core/` = Agent 内核）。
- `tests/` — pytest 套件（每个源模块一个模块）+ `data/` 固定装置。
- `examples/` — 可运行演示（`demo_turn.py`）。
