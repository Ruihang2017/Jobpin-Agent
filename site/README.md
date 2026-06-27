# `site/` — the published docs site (zero build)

## English
The only folder Netlify publishes (`netlify.toml` → `publish = "site"`). A
zero-build static site that renders the PRD and Production Plan and collects
reviewer feedback. Served as the web root, so `/` → `index.html`.

- `index.html` — page shell + the Netlify feedback form.
- `assets/` — JS/CSS for the viewer (incl. vendored libraries).
- `plan/` — the PRD + Production Plan markdown (the content the viewer fetches).
- `devlog/` — per-point bilingual study write-ups (the build journal).

## 中文
Netlify 唯一发布的文件夹（`netlify.toml` → `publish = "site"`）。零构建静态站点，渲染 PRD 与生产计划并收集
评审反馈。作为网站根目录提供服务，故 `/` → `index.html`。

- `index.html` — 页面外壳 + Netlify 反馈表单。
- `assets/` — 查看器的 JS/CSS（含第三方库）。
- `plan/` — PRD + 生产计划 markdown（查看器抓取的内容）。
- `devlog/` — 每个节点的双语学习记录（构建日志）。
