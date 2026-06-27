# `reference/` — read-only porting references (not published)

## English
External source kept for reference while porting — **not** a runtime dependency
and **not** published.

- `hermes/` — the Hermes Agent (Nous Research, MIT), a **pinned git submodule**.
  We *port* specific files from it into `agent/` (memory subsystem, injection
  defence) and *borrow* design (the conversation loop); we never import it at
  runtime. Populate it with `git submodule update --init --recursive`. Its
  internals are upstream's and are not documented per the per-folder convention.

## 中文
移植时保留作参考的外部源码——**不是**运行时依赖，也**不**发布。

- `hermes/` — Hermes Agent（Nous Research，MIT），一个**固定版本的 git 子模块**。我们从中*移植*特定文件到
  `agent/`（记忆子系统、注入防御）并*借鉴*设计（会话循环）；运行时绝不导入。用
  `git submodule update --init --recursive` 拉取。其内部属于上游，不按每文件夹约定记录。
