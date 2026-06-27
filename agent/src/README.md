# `agent/src/` — source root (src layout)

## English
Standard Python *src layout* root. Keeping the importable package under `src/`
(rather than at the project root) prevents accidental imports of the working
directory and makes packaging unambiguous. Tests add `src` to the path via
`pyproject.toml` (`pythonpath`).

- `jobpin_agent/` — the product package (the only thing here).

## 中文
标准 Python *src 布局* 根目录。把可导入的包放在 `src/` 下（而非项目根）可避免误导入工作目录，并使打包无歧义。
测试经 `pyproject.toml`（`pythonpath`）将 `src` 加入路径。

- `jobpin_agent/` — 产品包（此处唯一内容）。
