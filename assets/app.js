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
