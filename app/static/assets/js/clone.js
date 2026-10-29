'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const size = n => (n / 1073741824).toFixed(2) + ' GiB';
  let drives = [];
  async function read(path) {
    const response = await fetch(path, {cache: 'no-store'});
    const result = await response.json();
    if (!response.ok) throw Error(result.detail || 'Request failed');
    return result;
  }
  function changed() {
    $('plan').hidden = true;
    const drive = drives.find(item => item.id === $('drive').value);
    $('drive-details').textContent = drive ? [drive.path, drive.filesystem, drive.uuid, ...(drive.reasons || [])].join(' · ') : 'No eligible destination is mounted.';
    $('preview').disabled = !drive?.eligible;
  }
  async function reload() {
    try {
      drives = (await read('/clone/drives')).drives;
      $('drive').replaceChildren(...drives.filter(item => item.id).map(item => {
        const option = document.createElement('option');
        option.value = item.id;
        option.textContent = `${item.model || item.device} — ${item.path}${item.eligible ? ' — '+size(item.free_bytes)+' free' : ' — unavailable'}`;
        return option;
      }));
      const eligible = drives.find(item => item.eligible);
      if (eligible) $('drive').value = eligible.id;
      changed();
    } catch (error) { $('message').textContent = error.message; }
  }
  function list(id, rows) {
    $(id).replaceChildren(...rows.map(text => {
      const li = document.createElement('li'); li.textContent = text; return li;
    }));
  }
  $('preview').onclick = async () => {
    $('plan').hidden = true;
    $('message').textContent = 'Inspecting public files and available space…';
    try {
      const plan = await read('/clone/plan?'+new URLSearchParams({drive: $('drive').value, mode: $('mode').value}));
      $('capacity').textContent = `${size(plan.content_bytes)} content · ${size(plan.kit_bytes)} software allowance · ${size(plan.reserve_bytes)} reserve · ${plan.fits ? 'Fits' : 'Does not fit: choose a smaller selection or a larger drive'}`;
      list('included', ['Public configuration and setup software', ...plan.selected.map(item => `${item.title} — ${size(item.bytes)} (${item.file_count} files)`)]);
      list('skipped', plan.skipped.map(item => `${item.title} — ${item.reason}`));
      $('command').textContent = plan.fits ? plan.command : 'No copy command is available for a plan that does not fit.';
      $('copy').disabled = !plan.fits;
      $('plan').hidden = false;
      $('message').textContent = 'Preview only. No destination files were changed.';
    } catch (error) { $('message').textContent = error.message; }
  };
  $('copy').onclick = async () => {
    const text = $('command').textContent;
    try {
      if (navigator.clipboard && window.isSecureContext) await navigator.clipboard.writeText(text);
      else {
        const field = document.createElement('textarea'); field.value = text; document.body.append(field); field.select();
        const ok = document.execCommand('copy'); field.remove(); if (!ok) throw Error('Select and copy the command above.');
      }
      $('message').textContent = 'Command copied.';
    } catch (error) { $('message').textContent = error.message; }
  };
  $('terminal').href = `https://${location.hostname}:4200/`;
  $('drive').onchange = changed; $('mode').onchange = () => { $('plan').hidden = true; };
  $('reload').onclick = reload;
  async function progress() {
    try {
      const state = await read('/clone/status');
      $('progress').textContent = state.state === 'idle' ? 'No clone is running.' : `${state.state} · ${state.files_complete || 0}/${state.files_total || 0} files${state.current ? ' · '+state.current : ''}${state.error ? ' · '+state.error : ''}`;
    } catch (error) { $('progress').textContent = error.message; }
  }
  reload(); progress(); setInterval(progress, 5000);
})();
