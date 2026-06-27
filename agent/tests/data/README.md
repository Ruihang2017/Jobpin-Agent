# `agent/tests/data/` — test fixtures

## English
Static fixture files used by tests (kept out of the test code so diffs are clear).

- `system_prompt_golden.txt` — the expected byte-for-byte output of
  `build_system_prompt` for a fixed input. `test_system_prompt.py` compares
  against this to lock Key Invariant #1 (deterministic assembly). If you
  intentionally change the prompt format, regenerate this file.

## 中文
测试使用的静态固定装置文件（独立于测试代码，使差异清晰）。

- `system_prompt_golden.txt` — `build_system_prompt` 对固定输入的期望逐字节输出。`test_system_prompt.py`
  与之比对以锁定关键不变量 #1（确定性装配）。若你有意更改提示格式，请重新生成此文件。
