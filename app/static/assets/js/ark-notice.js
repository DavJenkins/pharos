/* Caretaker announcement: locally rendered Markdown, stored locally on this Ark. */
(() => {
  'use strict';
  const banner=document.querySelector('#ark-notice');
  if (!banner) return;
  const origin=document.createComment('Banner original position');banner.before(origin);
  const spacer=document.createElement('div');spacer.setAttribute('aria-hidden','true');document.body.append(spacer);
  function reserve() {
    const fixed=!banner.hidden && banner.dataset.bannerPosition==='bottom';
    const style=getComputedStyle(banner);
    spacer.style.height=fixed?(banner.getBoundingClientRect().height+parseFloat(style.bottom||0)+16)+'px':'0px';
  }
  const resize=new ResizeObserver(reserve);resize.observe(banner);
  function place(position) {
    if(position==='bottom'){if(banner.parentElement!==document.body)document.body.append(banner);}
    else if(position==='below-header'){
      const anchor=document.querySelector('#ark-notice-below-header');if(anchor && banner.parentElement!==anchor)anchor.append(banner);
    }else if(origin.nextSibling!==banner)origin.after(banner);
    reserve();
  }
  async function update() {
    if (document.hidden) return;
    try {
      const response=await fetch('/api/community/notice',{cache:'no-store'});
      if (!response.ok) return;
      const data=await response.json();
      if (typeof data.text!=='string') return;
      if(window.ArkNoticeMarkdown){window.ArkNoticeMarkdown.render(banner,data.text);window.ArkNoticeMarkdown.applyAppearance(banner,data);}else banner.textContent=data.text;banner.hidden=!data.text.trim();place(data.position);
    } catch (_) { /* Retain the last announcement during a temporary API interruption. */ }
  }
  window.addEventListener('ark-notice-changed',update);
  document.addEventListener('visibilitychange',update);
  update();setInterval(update,60000);
})();
