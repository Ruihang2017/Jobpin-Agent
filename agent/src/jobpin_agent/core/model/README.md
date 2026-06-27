# `core/model/` — the model layer

## English
The provider-agnostic boundary to LLM backends. The rest of the core depends only
on `ModelProvider` + the internal message types, so backends can be added or
swapped without touching the loop.

- `provider.py` — `ModelProvider` ABC (one `complete()` method).
- `fake_provider.py` — `FakeProvider`: scripted, offline backend for tests.
- `openai_provider.py` — `OpenAIProvider`: the first real adapter (OpenAI Chat
  Completions); the **only** file that knows OpenAI's wire format.

Future adapters (§1.11): Anthropic Claude, DeepSeek, and a local model — each
behind the same `ModelProvider` ABC.

## 中文
通往 LLM 后端的 provider 无关边界。内核其余部分只依赖 `ModelProvider` 与内部消息类型，故新增或替换后端无需改动循环。

- `provider.py` — `ModelProvider` 抽象基类（一个 `complete()` 方法）。
- `fake_provider.py` — `FakeProvider`：脚本化、离线的测试后端。
- `openai_provider.py` — `OpenAIProvider`：首个真实适配器（OpenAI Chat Completions）；**唯一**了解 OpenAI 线格式的文件。

未来适配器（§1.11）：Anthropic Claude、DeepSeek 与本地模型——均在同一 `ModelProvider` 抽象基类之后。
