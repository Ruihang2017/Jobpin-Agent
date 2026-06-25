# Jobpin Agent PRD Review Site — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a zero-build static site that renders the Jobpin Agent PRD and Production Plan (EN + 中文) and collects reviewer feedback via Netlify Forms, deployable to Netlify as a public unlisted URL.

**Architecture:** Plain static files served by Netlify with no build step. `index.html` is a single-page shell; ES-module JavaScript fetches the existing `plan/*.md` files, renders them in-browser with vendored marked.js + highlight.js, builds a scroll-spy table of contents, and wires a static Netlify form. The site reads the markdown directly from `plan/` (single source of truth — no copies).

**Tech Stack:** HTML/CSS/vanilla JS (ES modules), marked@12.0.2 (markdown→HTML), highlight.js 11.9.0 (code highlighting), Netlify static hosting + Netlify Forms.

## Global Constraints

- **Zero build step.** `netlify.toml` sets `publish = "."` with no build command. Netlify serves files as-is.
- **Single source of truth.** The site fetches `plan/01-PRD-EN.md`, `plan/01-PRD.md`, `plan/02-Production-Plan-EN.md`, `plan/02-Production-Plan.md` directly. Never copy or duplicate them.
- **Self-contained.** marked and highlight.js are vendored under `assets/vendor/` — no runtime CDN dependency. Pinned versions: marked@12.0.2, highlight.js cdn-assets@11.9.0.
- **Library globals.** Vendored libs load via plain `<script>` and expose `window.marked` and `window.hljs`. Application code uses ES modules (`<script type="module">`).
- **No accounts/apps for reviewers.** Feedback is a Netlify Forms `<form>` named exactly `feedback`, honeypot field named exactly `bot-field`, submitted via AJAX so reviewers stay on the page.
- **Unlisted.** Page carries `<meta name="robots" content="noindex, nofollow">` and an `X-Robots-Tag` header.
- **No automated test runner** (per the zero-tooling requirement). Verification per task = objective `curl`/`grep` smoke checks for static assets, plus explicit browser-observation steps with expected outcomes. The first browser-functional check is in Task 6, once all assets exist.

## DOM contract (ids/names used across files — keep verbatim)

| id / name | Where defined | Consumed by |
|---|---|---|
| `#content` | index.html | render.js (mount), app.js |
| `#toc` | index.html | render.js (TOC), app.js |
| `#doc-switch` (buttons `data-doc="prd"\|"plan"`) | index.html | app.js |
| `#lang-switch` (buttons `data-lang="en"\|"zh"`) | index.html | app.js |
| `#menu-btn` | index.html | app.js (mobile sidebar) |
| `#feedback`, `#feedback-fab` | index.html | app.js |
| `#feedback-form` (form `name="feedback"`, honeypot `bot-field`) | index.html | feedback.js |
| `#retry-btn` (class `link`) | render.js error HTML | app.js |
| `.form-status` | index.html | feedback.js |
| `renderDocument(path, contentEl, tocEl) → {retry}` | render.js | app.js |
| `initFeedback(form, getContext)` | feedback.js | app.js |

---

### Task 1: Project scaffold — directories, vendored libs, Netlify config, README

**Files:**
- Create: `assets/vendor/marked.min.js` (downloaded)
- Create: `assets/vendor/highlight.min.js` (downloaded)
- Create: `assets/vendor/github.min.css` (downloaded)
- Create: `netlify.toml`
- Create: `README.md`

**Interfaces:**
- Consumes: nothing.
- Produces: vendored `window.marked` / `window.hljs` libraries and the highlight theme stylesheet; Netlify publish config.

- [ ] **Step 1: Create the vendor directory and download the pinned libraries**

```bash
mkdir -p assets/vendor
curl -L -o assets/vendor/marked.min.js     https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js
curl -L -o assets/vendor/highlight.min.js  https://cdn.jsdelivr.net/npm/@highlightjs/cdn-assets@11.9.0/highlight.min.js
curl -L -o assets/vendor/github.min.css     https://cdn.jsdelivr.net/npm/@highlightjs/cdn-assets@11.9.0/styles/github.min.css
```

- [ ] **Step 2: Verify the libraries downloaded and are non-trivial**

Run:
```bash
ls -l assets/vendor && grep -l "marked" assets/vendor/marked.min.js && grep -l "hljs" assets/vendor/highlight.min.js
```
Expected: three files present; `marked.min.js` ~30–50 KB, `highlight.min.js` ~100+ KB, `github.min.css` a few KB; grep finds `marked` and `hljs` tokens (confirms not an HTML error page).

- [ ] **Step 3: Create `netlify.toml`**

```toml
# Zero-build static site. Netlify serves the repo root as-is.
[build]
  publish = "."
  command = ""

# Keep the unlisted review site out of search indexes.
[[headers]]
  for = "/*"
  [headers.values]
    X-Robots-Tag = "noindex, nofollow"
```

- [ ] **Step 4: Create `README.md`**

````markdown
# Jobpin Agent — PRD Review Site

A zero-build static site that renders the Jobpin Agent PRD and Production Plan
(English + 中文) and collects reviewer feedback via Netlify Forms. The site reads
the markdown in `plan/` directly — there is no build step and no duplicate copies.

## Run locally

The page fetches markdown over HTTP, so it needs a static server (not `file://`):

```bash
python -m http.server 8080
# then open http://localhost:8080
```

Note: the feedback form only truly submits on the deployed Netlify site (it posts
to Netlify's form backend). Locally you can see it render and validate.

## Deploy to Netlify

- **Git:** push this repo, then Netlify → "Add new site → Import from Git" → pick the
  repo. Build command: none. Publish directory: `.` (already set in `netlify.toml`).
- **Drag & drop:** drag the project folder into the Netlify dashboard.

After the first deploy:
1. Netlify → site → **Forms** → confirm a form named `feedback` is listed.
2. Forms → notifications → add an email notification to receive reviewer comments.
3. Share the URL (it's marked `noindex`; treat it as unlisted).

## Update content

Edit the markdown in `plan/` and redeploy. No build, no copies.

| Document | English | 中文 |
|---|---|---|
| PRD | `plan/01-PRD-EN.md` | `plan/01-PRD.md` |
| Production Plan | `plan/02-Production-Plan-EN.md` | `plan/02-Production-Plan.md` |
````

- [ ] **Step 5: Commit**

```bash
git add assets/vendor netlify.toml README.md
git commit -m "chore: scaffold static site (vendored libs, netlify config, readme)"
```

---

### Task 2: Stylesheet — clean responsive light theme

**Files:**
- Create: `assets/style.css`

**Interfaces:**
- Consumes: nothing (pure CSS).
- Produces: the visual theme + class names (`.topbar`, `.seg`, `.sidebar`, `.toc-link.active`, `.content`, `.table-wrap`, `.feedback`, `.fab`, `body.sidebar-open`) consumed by index.html, render.js, app.js.

- [ ] **Step 1: Create `assets/style.css`**

```css
:root {
  --bg: #ffffff;
  --bg-alt: #f6f8fa;
  --text: #1f2328;
  --muted: #656d76;
  --border: #d0d7de;
  --accent: #2563eb;
  --accent-soft: #dbeafe;
  --topbar-h: 56px;
  --sidebar-w: 300px;
  --max-content: 860px;
  --radius: 8px;
  --font: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", "Microsoft YaHei", Helvetica, Arial, sans-serif;
  --mono: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
}

* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body { margin: 0; font-family: var(--font); color: var(--text); background: var(--bg); line-height: 1.6; }

/* Topbar */
.topbar {
  position: sticky; top: 0; z-index: 30; height: var(--topbar-h);
  display: flex; align-items: center; gap: 16px; padding: 0 16px;
  background: var(--bg); border-bottom: 1px solid var(--border);
}
.brand { font-weight: 700; font-size: 16px; white-space: nowrap; }
.brand span { color: var(--muted); font-weight: 500; }
.controls { display: flex; gap: 12px; margin-left: auto; flex-wrap: wrap; }
.seg { display: inline-flex; border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; }
.seg button { border: 0; background: var(--bg); color: var(--muted); padding: 6px 12px; font-size: 13px; cursor: pointer; font-family: inherit; }
.seg button + button { border-left: 1px solid var(--border); }
.seg button.active { background: var(--accent); color: #fff; }
.icon-btn { display: none; border: 1px solid var(--border); background: var(--bg); border-radius: var(--radius); padding: 6px 10px; cursor: pointer; font-size: 16px; }

/* Layout */
.layout { display: flex; align-items: flex-start; }
.sidebar {
  position: sticky; top: var(--topbar-h); width: var(--sidebar-w); flex: 0 0 var(--sidebar-w);
  height: calc(100vh - var(--topbar-h)); overflow-y: auto;
  border-right: 1px solid var(--border); background: var(--bg-alt); padding: 16px 8px;
}
.toc { display: flex; flex-direction: column; }
.toc-link {
  display: block; padding: 4px 10px; font-size: 13px; color: var(--muted); text-decoration: none;
  border-radius: 6px; border-left: 2px solid transparent; line-height: 1.35;
}
.toc-link:hover { background: #eaeef2; color: var(--text); }
.toc-h3 { padding-left: 22px; font-size: 12.5px; }
.toc-link.active { color: var(--accent); background: var(--accent-soft); border-left-color: var(--accent); font-weight: 600; }
.toc-empty { color: var(--muted); font-size: 13px; padding: 8px 10px; }

.main { flex: 1 1 auto; min-width: 0; padding: 32px 40px 80px; }
.content { max-width: var(--max-content); margin: 0 auto; }

/* Markdown body */
.content h1 { font-size: 30px; margin: 0 0 8px; }
.content h2 { font-size: 23px; margin: 36px 0 12px; padding-bottom: 6px; border-bottom: 1px solid var(--border); scroll-margin-top: calc(var(--topbar-h) + 12px); }
.content h3 { font-size: 18px; margin: 26px 0 10px; scroll-margin-top: calc(var(--topbar-h) + 12px); }
.content h4 { font-size: 16px; margin: 20px 0 8px; scroll-margin-top: calc(var(--topbar-h) + 12px); }
.content p { margin: 12px 0; }
.content a { color: var(--accent); }
.content ul, .content ol { padding-left: 24px; }
.content li { margin: 4px 0; }
.content blockquote {
  margin: 16px 0; padding: 8px 16px; color: var(--muted); border-left: 4px solid var(--accent);
  background: var(--accent-soft); border-radius: 0 var(--radius) var(--radius) 0;
}
.content blockquote p { margin: 6px 0; }
.content code { font-family: var(--mono); font-size: 0.88em; background: var(--bg-alt); padding: 2px 5px; border-radius: 5px; }
.content pre { background: var(--bg-alt); border: 1px solid var(--border); border-radius: var(--radius); padding: 14px 16px; overflow-x: auto; }
.content pre code { background: none; padding: 0; font-size: 13px; }
.content hr { border: 0; border-top: 1px solid var(--border); margin: 28px 0; }
.table-wrap { overflow-x: auto; margin: 16px 0; }
.content table { border-collapse: collapse; width: 100%; font-size: 14px; }
.content th, .content td { border: 1px solid var(--border); padding: 8px 12px; text-align: left; vertical-align: top; }
.content thead th { background: var(--bg-alt); }
.content tbody tr:nth-child(even) { background: #fbfcfd; }

.status { color: var(--muted); padding: 24px 0; }
.status.error { color: #b42318; }
.link { background: none; border: 0; color: var(--accent); cursor: pointer; font: inherit; text-decoration: underline; padding: 0; }

/* Feedback */
.feedback { max-width: var(--max-content); margin: 56px auto 0; padding: 24px; border: 1px solid var(--border); border-radius: var(--radius); background: var(--bg-alt); }
.feedback h2 { margin: 0 0 4px; font-size: 20px; }
.feedback-note { margin: 0 0 16px; color: var(--muted); font-size: 14px; }
.field { display: flex; flex-direction: column; margin-bottom: 12px; }
.field label { font-size: 13px; font-weight: 600; margin-bottom: 4px; }
.field input, .field textarea { font-family: inherit; font-size: 14px; padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); }
.field textarea { resize: vertical; }
.hp { position: absolute; left: -5000px; }
.btn-primary { background: var(--accent); color: #fff; border: 0; padding: 10px 18px; border-radius: 6px; font-size: 14px; cursor: pointer; }
.btn-primary:hover { background: #1d4ed8; }
.form-status { min-height: 18px; font-size: 13px; color: var(--muted); margin: 8px 0 0; }
.form-status.error { color: #b42318; }
.thanks { color: #1a7f37; font-size: 15px; }

/* Floating feedback button */
.fab { position: fixed; right: 20px; bottom: 20px; z-index: 25; background: var(--accent); color: #fff; border: 0; padding: 12px 16px; border-radius: 999px; font-size: 14px; cursor: pointer; box-shadow: 0 4px 14px rgba(0,0,0,.18); }
.fab:hover { background: #1d4ed8; }

/* Responsive */
@media (max-width: 860px) {
  .icon-btn { display: inline-flex; }
  .sidebar {
    position: fixed; top: var(--topbar-h); left: 0; bottom: 0; height: auto;
    transform: translateX(-100%); transition: transform .2s ease; z-index: 20; width: 82%; max-width: 320px;
  }
  body.sidebar-open .sidebar { transform: translateX(0); box-shadow: 0 0 40px rgba(0,0,0,.25); }
  .main { padding: 20px 18px 80px; }
  .controls { gap: 8px; }
  .brand { font-size: 14px; }
}
```

- [ ] **Step 2: Verify the file exists and parses key rules**

Run:
```bash
grep -c "sidebar-open\|toc-link.active\|table-wrap\|btn-primary" assets/style.css
```
Expected: count ≥ 4 (all key class hooks present).

- [ ] **Step 3: Commit**

```bash
git add assets/style.css
git commit -m "feat: add site stylesheet (responsive light theme)"
```

---

### Task 3: Markdown rendering engine — `render.js`

**Files:**
- Create: `assets/render.js`

**Interfaces:**
- Consumes: `window.marked`, `window.hljs` (loaded globally by index.html before this module).
- Produces: `export async function renderDocument(path, contentEl, tocEl) → { retry: boolean }`. Fetches `path`, renders markdown into `contentEl`, slugs headings, highlights code, wraps tables, builds the TOC in `tocEl`, and starts scroll-spy. Returns `{ retry: true }` only when the fetch failed and an error UI with `#retry-btn` was rendered.

- [ ] **Step 1: Create `assets/render.js`**

```js
// Renders a markdown document into the page and builds its table of contents.
// Depends on global window.marked and window.hljs (loaded by index.html).

let activeObserver = null;

export async function renderDocument(path, contentEl, tocEl) {
  contentEl.innerHTML = '<p class="status">Loading…</p>';
  let md;
  try {
    const res = await fetch(path, { cache: 'no-cache' });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    md = await res.text();
  } catch (err) {
    contentEl.innerHTML =
      '<div class="status error">Couldn’t load this document (' + err.message +
      '). <button id="retry-btn" class="link">Retry</button></div>';
    tocEl.innerHTML = '';
    return { retry: true };
  }

  contentEl.innerHTML = window.marked.parse(md);
  slugHeadings(contentEl);
  enhance(contentEl);
  buildToc(contentEl, tocEl);
  scrollSpy(contentEl, tocEl);
  window.scrollTo(0, 0);
  return { retry: false };
}

// Give every heading a stable, unique id (works for English and CJK text).
function slugHeadings(root) {
  const used = new Set();
  root.querySelectorAll('h1, h2, h3, h4').forEach((h) => {
    let base = h.textContent.trim().toLowerCase()
      .replace(/[^\w一-鿿]+/g, '-')
      .replace(/^-+|-+$/g, '');
    if (!base) base = 'section';
    let slug = base;
    let i = 1;
    while (used.has(slug)) { slug = base + '-' + i; i += 1; }
    used.add(slug);
    h.id = slug;
  });
}

// Highlight code blocks and make wide tables horizontally scrollable.
function enhance(root) {
  if (window.hljs) {
    root.querySelectorAll('pre code').forEach((block) => window.hljs.highlightElement(block));
  }
  root.querySelectorAll('table').forEach((table) => {
    if (table.parentElement && table.parentElement.classList.contains('table-wrap')) return;
    const wrap = document.createElement('div');
    wrap.className = 'table-wrap';
    table.parentNode.insertBefore(wrap, table);
    wrap.appendChild(table);
  });
}

// Build the sidebar TOC from H2/H3 headings.
function buildToc(root, tocEl) {
  tocEl.innerHTML = '';
  const headings = root.querySelectorAll('h2, h3');
  if (!headings.length) {
    tocEl.innerHTML = '<p class="toc-empty">No sections</p>';
    return;
  }
  headings.forEach((h) => {
    const a = document.createElement('a');
    a.href = '#' + h.id;
    a.textContent = h.textContent;
    a.className = 'toc-link toc-' + h.tagName.toLowerCase();
    a.dataset.target = h.id;
    a.addEventListener('click', () => document.body.classList.remove('sidebar-open'));
    tocEl.appendChild(a);
  });
}

// Highlight the TOC entry for the heading currently in view.
function scrollSpy(root, tocEl) {
  if (activeObserver) activeObserver.disconnect();
  const links = new Map();
  tocEl.querySelectorAll('.toc-link').forEach((a) => links.set(a.dataset.target, a));
  activeObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      tocEl.querySelectorAll('.toc-link.active').forEach((x) => x.classList.remove('active'));
      const link = links.get(entry.target.id);
      if (link) {
        link.classList.add('active');
        link.scrollIntoView({ block: 'nearest' });
      }
    });
  }, { rootMargin: '0px 0px -75% 0px', threshold: 0 });
  root.querySelectorAll('h2, h3').forEach((h) => activeObserver.observe(h));
}
```

- [ ] **Step 2: Verify the module is present with the expected export and helpers**

Run:
```bash
grep -c "export async function renderDocument\|function slugHeadings\|function buildToc\|function scrollSpy" assets/render.js
```
Expected: count = 4 (export + three helpers all present).

- [ ] **Step 3: Commit**

```bash
git add assets/render.js
git commit -m "feat: add markdown rendering engine with TOC and scroll-spy"
```

---

### Task 4: Feedback submission — `feedback.js`

**Files:**
- Create: `assets/feedback.js`

**Interfaces:**
- Consumes: a `<form id="feedback-form" name="feedback">` element and a `getContext()` callback returning a short string (e.g. `"PRD (EN)"`).
- Produces: `export function initFeedback(form, getContext)`. Intercepts submit, posts URL-encoded data (including `form-name=feedback`) to `/` for Netlify Forms, replaces the form with a thank-you message on success, shows an inline error on failure. Sets the section field's placeholder to the current context on focus.

- [ ] **Step 1: Create `assets/feedback.js`**

```js
// Submits the feedback form to Netlify Forms via AJAX so the reviewer stays on the page.

export function initFeedback(form, getContext) {
  const section = form.querySelector('[name="section"]');
  if (section && getContext) {
    form.addEventListener('focusin', () => {
      if (!section.value) section.placeholder = getContext();
    });
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const status = form.querySelector('.form-status');
    const data = {};
    new FormData(form).forEach((value, key) => { data[key] = value; });

    if (status) { status.textContent = 'Sending…'; status.className = 'form-status'; }

    try {
      const res = await fetch('/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: encode(data),
      });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      form.innerHTML = '<p class="thanks">Thanks — your feedback was sent. 🙏</p>';
    } catch (err) {
      if (status) {
        status.textContent = 'Sorry, that didn’t send (' + err.message + '). Please try again.';
        status.className = 'form-status error';
      }
    }
  });
}

function encode(data) {
  return Object.keys(data)
    .map((key) => encodeURIComponent(key) + '=' + encodeURIComponent(data[key]))
    .join('&');
}
```

- [ ] **Step 2: Verify the module is present with the expected export**

Run:
```bash
grep -c "export function initFeedback\|form-name\|application/x-www-form-urlencoded" assets/feedback.js
```
Expected: count = 3.

- [ ] **Step 3: Commit**

```bash
git add assets/feedback.js
git commit -m "feat: add Netlify Forms feedback submission (AJAX)"
```

---

### Task 5: Application entry — `app.js`

**Files:**
- Create: `assets/app.js`

**Interfaces:**
- Consumes: `renderDocument` from `./render.js`, `initFeedback` from `./feedback.js`; DOM ids per the DOM contract.
- Produces: the running app — document/language state with `localStorage` persistence, control wiring, mobile sidebar toggle, floating feedback button, initial load.

- [ ] **Step 1: Create `assets/app.js`**

```js
import { renderDocument } from './render.js';
import { initFeedback } from './feedback.js';

const DOCS = {
  prd:  { label: 'PRD',             en: 'plan/01-PRD-EN.md',             zh: 'plan/01-PRD.md' },
  plan: { label: 'Production Plan', en: 'plan/02-Production-Plan-EN.md', zh: 'plan/02-Production-Plan.md' },
};
const LANG_LABEL = { en: 'EN', zh: '中文' };

const state = {
  doc: localStorage.getItem('jobpin.doc') || 'prd',
  lang: localStorage.getItem('jobpin.lang') || 'en',
};
if (!DOCS[state.doc]) state.doc = 'prd';
if (state.lang !== 'en' && state.lang !== 'zh') state.lang = 'en';

if (window.marked) window.marked.setOptions({ gfm: true, breaks: false });

const contentEl = document.getElementById('content');
const tocEl = document.getElementById('toc');

async function load() {
  syncControls();
  const path = DOCS[state.doc][state.lang];
  const result = await renderDocument(path, contentEl, tocEl);
  if (result.retry) {
    const btn = document.getElementById('retry-btn');
    if (btn) btn.addEventListener('click', load);
  }
}

function syncControls() {
  document.querySelectorAll('#doc-switch button').forEach((b) =>
    b.classList.toggle('active', b.dataset.doc === state.doc));
  document.querySelectorAll('#lang-switch button').forEach((b) =>
    b.classList.toggle('active', b.dataset.lang === state.lang));
  localStorage.setItem('jobpin.doc', state.doc);
  localStorage.setItem('jobpin.lang', state.lang);
}

document.querySelectorAll('#doc-switch button').forEach((b) =>
  b.addEventListener('click', () => { state.doc = b.dataset.doc; load(); }));
document.querySelectorAll('#lang-switch button').forEach((b) =>
  b.addEventListener('click', () => { state.lang = b.dataset.lang; load(); }));

const menuBtn = document.getElementById('menu-btn');
if (menuBtn) menuBtn.addEventListener('click', () => document.body.classList.toggle('sidebar-open'));

const fab = document.getElementById('feedback-fab');
if (fab) fab.addEventListener('click', () =>
  document.getElementById('feedback').scrollIntoView({ behavior: 'smooth' }));

const form = document.getElementById('feedback-form');
if (form) initFeedback(form, () => DOCS[state.doc].label + ' (' + LANG_LABEL[state.lang] + ')');

load();
```

- [ ] **Step 2: Verify imports and the document map are consistent with render.js/feedback.js and the real markdown paths**

Run:
```bash
grep -c "from './render.js'\|from './feedback.js'\|plan/01-PRD-EN.md\|plan/02-Production-Plan-EN.md" assets/app.js
ls plan/01-PRD-EN.md plan/01-PRD.md plan/02-Production-Plan-EN.md plan/02-Production-Plan.md
```
Expected: first command count = 4; `ls` lists all four existing markdown files (confirms the DOCS paths resolve).

- [ ] **Step 3: Commit**

```bash
git add assets/app.js
git commit -m "feat: add app entry (state, controls, persistence, init)"
```

---

### Task 6: Page shell `index.html` + full end-to-end verification

**Files:**
- Create: `index.html`

**Interfaces:**
- Consumes: `assets/style.css`, `assets/vendor/github.min.css`, `assets/vendor/marked.min.js`, `assets/vendor/highlight.min.js`, `assets/app.js`; provides every DOM id/name in the DOM contract.
- Produces: the deployable page, including the static Netlify `feedback` form (so Netlify detects it at deploy).

- [ ] **Step 1: Create `index.html`**

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="robots" content="noindex, nofollow" />
  <title>Jobpin Agent — Docs</title>
  <link rel="stylesheet" href="assets/vendor/github.min.css" />
  <link rel="stylesheet" href="assets/style.css" />
</head>
<body>
  <header class="topbar">
    <button id="menu-btn" class="icon-btn" aria-label="Toggle sections">☰</button>
    <div class="brand">Jobpin Agent <span>· Docs</span></div>
    <nav class="controls">
      <div class="seg" id="doc-switch">
        <button data-doc="prd">PRD</button>
        <button data-doc="plan">Production Plan</button>
      </div>
      <div class="seg" id="lang-switch">
        <button data-lang="en">EN</button>
        <button data-lang="zh">中文</button>
      </div>
    </nav>
  </header>

  <div class="layout">
    <aside class="sidebar">
      <nav id="toc" class="toc"></nav>
    </aside>
    <main class="main">
      <article id="content" class="content"></article>

      <section id="feedback" class="feedback">
        <h2>Leave feedback</h2>
        <p class="feedback-note">Your comments go straight to the team — no account needed.</p>
        <form name="feedback" method="POST" data-netlify="true" netlify-honeypot="bot-field" id="feedback-form">
          <input type="hidden" name="form-name" value="feedback" />
          <p class="hp"><label>Leave this empty <input name="bot-field" /></label></p>
          <div class="field">
            <label for="fb-name">Name</label>
            <input id="fb-name" type="text" name="name" required />
          </div>
          <div class="field">
            <label for="fb-email">Email (optional)</label>
            <input id="fb-email" type="email" name="email" />
          </div>
          <div class="field">
            <label for="fb-section">Which section</label>
            <input id="fb-section" type="text" name="section" />
          </div>
          <div class="field">
            <label for="fb-comment">Comment</label>
            <textarea id="fb-comment" name="comment" rows="4" required></textarea>
          </div>
          <p class="form-status" role="status"></p>
          <button type="submit" class="btn-primary">Send feedback</button>
        </form>
      </section>
    </main>
  </div>

  <button id="feedback-fab" class="fab" aria-label="Leave feedback">💬 Feedback</button>

  <script src="assets/vendor/marked.min.js"></script>
  <script src="assets/vendor/highlight.min.js"></script>
  <script type="module" src="assets/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Static smoke check — serve locally and confirm assets resolve**

Run:
```bash
python -m http.server 8080 &
sleep 1
curl -s -o /dev/null -w "index:%{http_code}\n"   http://localhost:8080/
curl -s -o /dev/null -w "app:%{http_code}\n"     http://localhost:8080/assets/app.js
curl -s -o /dev/null -w "render:%{http_code}\n"  http://localhost:8080/assets/render.js
curl -s -o /dev/null -w "marked:%{http_code}\n"  http://localhost:8080/assets/vendor/marked.min.js
curl -s -o /dev/null -w "prd:%{http_code}\n"     http://localhost:8080/plan/01-PRD-EN.md
curl -s http://localhost:8080/ | grep -c 'data-netlify="true"'
```
Expected: every status code is `200`; the final grep prints `1` (the Netlify form is in the served HTML). Leave the server running for Step 3 (stop it afterward with `kill %1`).

- [ ] **Step 3: Browser-functional check (manual, exact expectations)**

Open `http://localhost:8080/` in a browser and confirm:
1. The PRD (English) renders with headings, tables, and highlighted code blocks; the title bar shows "Jobpin Agent · Docs".
2. The left sidebar lists the PRD's sections; clicking an entry scrolls to that heading; scrolling highlights the current section in the sidebar.
3. Click **中文** → the same document reloads in Chinese; the TOC updates. Click **Production Plan** → the roadmap loads; TOC updates to its sections.
4. Reload the page → it reopens on the last-selected document and language (localStorage persistence).
5. Narrow the window below ~860px → the ☰ button appears and toggles the sidebar as an overlay; wide tables scroll horizontally instead of overflowing.
6. The 💬 Feedback button scrolls to the form; submitting with empty Name/Comment is blocked by the browser's required-field validation.

(The form's actual network submit returns an error locally — that's expected; it only succeeds on Netlify. Verified in Step 5.)

Stop the local server: `kill %1`

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat: add page shell and Netlify feedback form"
```

- [ ] **Step 5: Deploy verification (post-deploy, on Netlify)**

After deploying per `README.md`:
1. Open the Netlify site URL; repeat the Step 3 browser checks on the live site.
2. Submit the feedback form with a test Name + Comment → the form is replaced with "Thanks — your feedback was sent."
3. Netlify dashboard → **Forms** → confirm a form named `feedback` exists and the test submission appears.
4. Forms → notifications → add an email notification.

---

## Self-Review

**1. Spec coverage** (each spec requirement → task):
- Render all four docs, typography/tables/code/blockquotes → Task 2 (CSS) + Task 3 (render). ✓
- Document switcher → Task 5 (`#doc-switch` wiring) + Task 6 (markup). ✓
- Language toggle + localStorage persistence → Task 5. ✓
- TOC (H2+H3) + scroll-spy → Task 3. ✓
- Netlify Forms feedback (Name/Email/Section/Comment, AJAX, honeypot) → Task 4 (submit) + Task 6 (static form markup). ✓
- Zero build / single source of truth / self-contained vendoring → Task 1 + Global Constraints. ✓
- Responsive + collapsing sidebar + horizontal table scroll → Task 2 (media query) + Task 3 (table-wrap). ✓
- Error handling (md fetch fail w/ retry; submit fail keeps input; required fields) → Task 3 (retry), Task 4 (error path), Task 6 (HTML5 `required`). ✓
- Light theme → Task 2. ✓
- Deployment (publish=".", noindex header, Forms notification) → Task 1 (netlify.toml) + Task 6 Step 5. ✓
- Out-of-scope items (auth/search/dark mode/threaded comments) → not implemented. ✓

**2. Placeholder scan:** No TBD/TODO; every code step contains complete, runnable content. ✓

**3. Type/name consistency:** `renderDocument(path, contentEl, tocEl) → {retry}` defined in Task 3, called identically in Task 5. `initFeedback(form, getContext)` defined in Task 4, called identically in Task 5. DOM ids/names match between Task 6 markup and the JS consumers (verified against the DOM contract table). Document paths in Task 5's `DOCS` match the real files checked in Task 5 Step 2. ✓
