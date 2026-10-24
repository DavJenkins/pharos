// Only our exact Ark capture page is matched; passwords and SSH keys never enter this script.
document.documentElement.dataset.arkCapture = 'ready';
document.addEventListener('click', async event => {
  const publisher=event.target.closest('a[data-arm-id]');
  if (publisher && event.isTrusted) {
    event.preventDefault();
    const result=await chrome.runtime.sendMessage({action:'arm',id:publisher.dataset.armId});
    if (!result.error) window.open(publisher.href,'_blank','noopener');
    return;
  }
  if (event.target.closest('#retry-capture') && event.isTrusted) {
    await chrome.runtime.sendMessage({action:'retry'});return;
  }
  const button = event.target.closest('button[data-capture-id]');
  if (!button || !event.isTrusted) return;
  button.disabled = true;
  const status = button.parentElement.querySelector('[role=status]');
  try {
    const result = await chrome.runtime.sendMessage({action:'start', id:button.dataset.captureId});
    status.textContent = result.error || 'Downloading in Chrome; the completed file will be imported automatically.';
  } catch (e) { status.textContent = e.message; button.disabled = false; }
});
async function refresh() {
  try {
    const result = await chrome.runtime.sendMessage({action:'status'});
    for (const button of document.querySelectorAll('button[data-capture-id]')) {
      const row = result[button.dataset.captureId];
      if (!row) continue;
      button.parentElement.querySelector('[role=status]').textContent = row.message;
      button.disabled = ['downloading','importing','installed'].includes(row.state);
    }
  } catch (_) { /* extension reload; refresh the page to reconnect */ }
}
refresh(); setInterval(refresh, 1500);
