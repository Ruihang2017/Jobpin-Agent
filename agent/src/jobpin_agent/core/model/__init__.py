"""Model layer — the provider-agnostic boundary to LLM backends.

EN —
Defines the ``ModelProvider`` abstraction and its adapters. The rest of the core
depends only on ``ModelProvider`` + the internal message types, never on a
vendor's wire format. ``FakeProvider`` powers offline/deterministic tests;
``OpenAIProvider`` is the first real adapter (OpenAI is the dev/pilot default per
PRD §11.3). Claude / DeepSeek / local adapters slot in here behind the same ABC
at §1.11 — adding a backend must not require touching the loop.

中文 —
定义 ``ModelProvider`` 抽象及其适配器。内核其余部分只依赖 ``ModelProvider`` 与内部消息类型，
绝不依赖某厂商的线格式。``FakeProvider`` 支撑离线/确定性测试；``OpenAIProvider`` 是首个真实适配器
（按 PRD §11.3，OpenAI 为开发/试点默认）。Claude / DeepSeek / 本地适配器将在 §1.11 以同一抽象基类
接入——新增后端不应改动循环。
"""
