/* Caretaker announcement: plain text, stored locally on this Ark. */
(() => {
  'use strict';
  const banner=document.querySelector('#ark-notice');
  if (!banner) return;
  async function update() {
    if (document.hidden) return;
    try {
      const response=await fetch('/api/community/notice',{cache:'no-store'});
      if (!response.ok) return;
      const data=await response.json();
      if (typeof data.text!=='string') return;
      banner.textContent=data.text;banner.hidden=!data.text;
    } catch (_) { /* Retain the last announcement during a temporary API interruption. */ }
  }
  window.addEventListener('ark-notice-changed',update);
  document.addEventListener('visibilitychange',update);
  update();setInterval(update,60000);
})();
