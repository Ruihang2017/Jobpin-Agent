# Jobpin Agent — PRD Review Site (Design Spec)

| Item | Value |
|---|---|
| Date | 2026-06-25 |
| Status | Approved (brainstorming output) |
| Author | horace.hou |
| Goal | A static, Netlify-hosted site that renders the Jobpin Agent PRD and Production Plan (EN + 中文) and lets reviewers leave feedback without creating accounts or installing anything |

## 1. Purpose & Context

The `plan/` directory holds four large markdown documents:

- `plan/01-PRD-EN.md` — Product Requirements Document (English)
- `plan/01-PRD.md` — Product Requirements Document (中文)
- `plan/02-Production-Plan-EN.md` — Industrial-grade production roadmap (English)
- `plan/02-Production-Plan.md` — Industrial-grade production roadmap (中文)

We want to host these as a clean, readable website on Netlify (public, unlisted URL) so colleagues — including non-technical reviewers (Legal, HR) — can read them and leave feedback. This is an internal review of a confidential-but-not-secret PRD; no hard auth is required.

## 2. Requirements

### Functional
- Render all four markdown documents with good typography, GFM tables, syntax-highlighted code blocks, and styled blockquotes/callouts.
- **Document switcher:** PRD ⇄ Production Plan.
- **Language toggle:** EN ⇄ 中文 (per document). Remembered across visits via `localStorage`.
- **Table of contents:** auto-generated from the active document's headings (H2 + H3), with scroll-spy highlighting the section currently in view. Clicking a TOC entry scrolls to that heading.
- **Feedback:** a Netlify Forms-backed feedback box on each document plus a floating "Leave feedback" button. Fields: **Name**, **Email (optional)**, **Which section**, **Comment**. Submitted via AJAX so the reviewer stays on the page and sees a confirmation. No account or app required for reviewers. Submissions are delivered to the site owner via the Netlify dashboard + email notifications.
- Anti-spam: honeypot field on the form.

### Non-Functional
- **Zero build step.** Netlify serves static files directly; updating content = edit the markdown in `plan/` and redeploy.
- **Single source of truth.** The site reads directly from the existing `plan/*.md` files — no duplicate copies.
- **Self-contained.** Markdown/highlighting libraries are vendored locally (not loaded from a CDN at runtime) so the site is reliable and has no external runtime dependency.
- **Responsive.** Works on desktop, tablet, and mobile; the sidebar collapses on small screens; wide tables scroll horizontally.
- **Clean, professional light theme.**

### Out of scope (YAGNI)
- Authentication / login / password gate
- Full-text search
- Dark mode
- Threaded/public comments (reviewers seeing each other's comments)
- Multi-page routing / per-document URLs

## 3. Architecture

Approach **A: zero-build, client-side rendering** (chosen over a static-site generator or a pre-render build script because it is the fastest to ship and has nothing in the build pipeline to break).

```
repo root  (Netlify publish directory = ".")
├── index.html          shell: top bar, sidebar, content mount, feedback form
├── assets/
│   ├── style.css        light theme, layout, responsive rules
│   ├── app.js           fetch + render md, build TOC, scroll-spy, toggles, AJAX form
│   └── vendor/
│       ├── marked.min.js          markdown → HTML (GFM)
│       ├── highlight.min.js        code syntax highlighting
│       └── highlight-theme.css     highlight.js stylesheet
├── plan/                EXISTING markdown — the single source of truth (unchanged)
│   ├── 01-PRD-EN.md
│   ├── 01-PRD.md
│   ├── 02-Production-Plan-EN.md
│   └── 02-Production-Plan.md
├── netlify.toml         publish = ".", no build command
└── README.md            deploy + update instructions
```

### Data flow
1. On load, `app.js` reads the last `{document, language}` selection from `localStorage` (default: PRD / EN).
2. It maps `{document, language}` → a file path in `plan/`:
   | Document | EN | 中文 |
   |---|---|---|
   | PRD | `plan/01-PRD-EN.md` | `plan/01-PRD.md` |
   | Production Plan | `plan/02-Production-Plan-EN.md` | `plan/02-Production-Plan.md` |
3. `fetch()` the markdown → render to HTML with `marked` → inject into the content column.
4. Assign slug `id`s to headings during/after render; build the TOC from H2/H3; wire scroll-spy via `IntersectionObserver`.
5. Toggling document or language re-runs steps 2–4 and persists the new selection.

### Modules (single-purpose units in `app.js`)
- **`config`** — the document/language → path map and labels.
- **`renderDoc(path)`** — fetch, convert markdown, slug headings, inject; handles fetch errors with an inline message.
- **`buildToc()`** — read rendered H2/H3 headings, produce the sidebar list.
- **`scrollSpy()`** — `IntersectionObserver` to highlight the active TOC entry.
- **`state`** — current selection + `localStorage` persistence.
- **`feedback()`** — AJAX submit to Netlify, success/error UI, prefill the "Which section" hint with the current document/language.

### Netlify Forms detail
Netlify detects forms by scanning deployed HTML at deploy time, so the feedback `<form>` is **static HTML in `index.html`** (not JS-injected), with `data-netlify="true"`, `name="feedback"`, and `netlify-honeypot="bot-field"`. The visible form posts via `fetch()` (URL-encoded body including `form-name=feedback`) to keep the reviewer on the page; on success the form is replaced with a thank-you message.

## 4. Error Handling
- **Markdown fetch fails** (network/404): show an inline, friendly error in the content column with a retry link; do not blank the page.
- **Feedback submit fails:** keep the user's typed input, show an error, allow retry.
- **Empty required fields:** native HTML5 `required` validation on Name + Comment before submit.

## 5. Testing / Verification
Manual verification (documented in README), since this is a static content site:
- Both documents render in both languages; tables and code blocks display correctly.
- TOC reflects the active document and scroll-spy tracks the visible section.
- Language/document selection persists across reload.
- Feedback form submits successfully on the deployed Netlify site and the submission appears in the Netlify dashboard.
- Layout is usable on a narrow (mobile) viewport.

## 6. Deployment
- Push the repo to a Git provider and connect it to Netlify, **or** drag-and-drop the folder into Netlify.
- No build command; publish directory = repo root (`.`) per `netlify.toml`.
- After first deploy, confirm the "feedback" form is listed under Netlify → Forms, and configure an email notification.
- Share the resulting unlisted URL with reviewers.
