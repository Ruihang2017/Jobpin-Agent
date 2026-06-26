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
      `<div class="status error">Couldn't load this document (${err.message}). <button id="retry-btn" class="link">Retry</button></div>`;
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
