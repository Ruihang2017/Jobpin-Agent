# `site/assets/` — viewer front-end assets

## English
The JavaScript and CSS that power the docs viewer. No build step — these are
loaded directly by `index.html`.

- `app.js` — entry point: doc/lang state, controls, persistence, init.
- `render.js` — fetches a markdown doc, renders it, builds the TOC, scroll-spy.
- `feedback.js` — wires the Netlify feedback form.
- `style.css` — site styles.
- `vendor/` — third-party libraries, vendored (not edited here): `marked` (Markdown
  → HTML), `highlight.js` (code highlighting), and its GitHub theme CSS. Excluded
  from the per-folder-doc convention as third-party.

## 中文
驱动文档查看器的 JavaScript 与 CSS。无构建步骤——由 `index.html` 直接加载。

- `app.js` — 入口：文档/语言状态、控件、持久化、初始化。
- `render.js` — 抓取 markdown 文档、渲染、构建目录、滚动高亮。
- `feedback.js` — 接线 Netlify 反馈表单。
- `style.css` — 站点样式。
- `vendor/` — 第三方库，已 vendoring（此处不编辑）：`marked`（Markdown → HTML）、`highlight.js`（代码高亮）及其
  GitHub 主题 CSS。作为第三方，排除在每文件夹文档约定之外。
