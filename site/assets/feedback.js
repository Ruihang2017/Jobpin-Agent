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

    if (status) { status.textContent = 'Sending…'; status.className = 'form-status'; }

    try {
      const res = await fetch('/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams(new FormData(form)).toString(),
      });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      form.innerHTML = '<p class="thanks">Thanks — your feedback was sent. 🙏</p>';
    } catch (err) {
      if (status) {
        status.textContent = `Sorry, that didn't send (${err.message}). Please try again.`;
        status.className = 'form-status error';
      }
    }
  });
}
