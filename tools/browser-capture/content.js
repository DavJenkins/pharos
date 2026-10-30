// Only our exact Ark capture page is matched; passwords and SSH keys never enter this script.
document.documentElement.dataset.arkCapture = 'ready';
const delivered = new Map();
document.addEventListener('click', async event => {
  if (event.target.closest('#check-updates') && event.isTrusted) {
    const button=event.target.closest('#check-updates');button.disabled=true;
    try { await chrome.runtime.sendMessage({action:'check_updates'}); }
    finally {button.disabled=false;document.dispatchEvent(new Event('ark-capture-refresh'));}
    return;
  }
  const publisher=event.target.closest('a[data-arm-id]');
  if (publisher && event.isTrusted) {
    event.preventDefault();
    const result=await chrome.runtime.sendMessage({action:'arm',id:publisher.dataset.armId,expected_sha256:publisher.dataset.expectedHash});
    if (!result.error) window.open(publisher.href,'_blank','noopener');
    return;
  }
  if (event.target.closest('#retry-capture') && event.isTrusted) {
    const output=document.querySelector('#update-status');
    try{const result=await chrome.runtime.sendMessage({action:'retry'});if(output)output.textContent=result.error||result.message;}
    catch(e){if(output)output.textContent=e.message;}
    return;
  }
  const button = event.target.closest('button[data-capture-id]');
  if (!button || !event.isTrusted) return;
  button.disabled = true;
  const status = button.parentElement.querySelector('[role=status]');
  try {
    const result = await chrome.runtime.sendMessage({action:'start', id:button.dataset.captureId,expected_sha256:button.dataset.expectedHash});
    status.textContent = result.error || 'Downloading in Chrome; the completed file will be imported automatically.';
  } catch (e) { status.textContent = e.message; button.disabled = false; }
});
async function refresh() {
  try {
    const result = await chrome.runtime.sendMessage({action:'status'});
    const updates=result.__updates__;
    if(updates && document.querySelector('#update-status'))document.querySelector('#update-status').textContent=updates.message;
    for (const button of document.querySelectorAll('button[data-capture-id]')) {
      const row = result[button.dataset.captureId];
      if (!row) continue;
      button.parentElement.querySelector('[role=status]').textContent = row.message;
      button.disabled = ['downloading','importing'].includes(row.state) || row.state==='installed' && !button.dataset.expectedHash;
      if(row.state==='installed' && delivered.get(button.dataset.captureId)!==row.message) {
        delivered.set(button.dataset.captureId,row.message);document.dispatchEvent(new Event('ark-capture-refresh'));
      }
    }
  } catch (_) { /* extension reload; refresh the page to reconnect */ }
}
refresh(); setInterval(refresh, 1500);
