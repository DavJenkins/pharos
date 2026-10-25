/* Caretaker announcement: locally rendered Markdown, stored locally on this Ark. */
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
      if(window.ArkNoticeMarkdown){window.ArkNoticeMarkdown.render(banner,data.text);window.ArkNoticeMarkdown.applyColor(banner,data.color);}else banner.textContent=data.text;banner.hidden=!data.text.trim();
    } catch (_) { /* Retain the last announcement during a temporary API interruption. */ }
  }
  window.addEventListener('ark-notice-changed',update);
  document.addEventListener('visibilitychange',update);
  update();setInterval(update,60000);
})();
