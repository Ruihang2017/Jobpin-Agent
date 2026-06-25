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
        status.textContent = 'Sorry, that didn't send (' + err.message + '). Please try again.';
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
