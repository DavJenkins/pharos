/* Availability only: no form values are collected or submitted. */
(async () => {
  try {
    const response = await fetch('/api/library', {cache:'no-store'});
    if (!response.ok) return;
    const inventory = await response.json();
    const installed = new Set(inventory.installed.map(item => item.id));
    document.querySelectorAll('[data-form-id]').forEach(row => {
      if (installed.has(row.dataset.formId)) return;
      const file = row.querySelector('[data-form-file]');
      file.removeAttribute('href');
      const notice = document.createElement('strong');
      notice.textContent = ' — No longer installed on the Ark';
      file.after(notice);
    });
  } catch (_) { /* Original links remain usable if the management API is unavailable. */ }
})();
