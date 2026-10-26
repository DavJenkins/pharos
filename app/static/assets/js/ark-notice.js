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
  let current=null,lastRendered='';
  function redraw() {
    if(!current || document.hidden)return;
    const now=new Date(),key=window.ArkNoticeMarkdown?.expandVariables(current.text,now)||current.text;
    if(key===lastRendered)return;
    lastRendered=key;
    if(window.ArkNoticeMarkdown)window.ArkNoticeMarkdown.render(banner,current.text,{variables:true,now});else banner.textContent=current.text;
    reserve();
  }
  async function update() {
    if (document.hidden) return;
    try {
      const response=await fetch('/api/community/notice',{cache:'no-store'});
      if (!response.ok) return;
      const data=await response.json();
      if (typeof data.text!=='string') return;
      current=data;lastRendered='';redraw();if(window.ArkNoticeMarkdown)window.ArkNoticeMarkdown.applyAppearance(banner,data);banner.hidden=!data.text.trim();place(data.position);
    } catch (_) { /* Retain the last announcement during a temporary API interruption. */ }
  }
  window.addEventListener('ark-notice-changed',update);
  document.addEventListener('visibilitychange',update);
  update();setInterval(update,60000);setInterval(redraw,1000);
})();
