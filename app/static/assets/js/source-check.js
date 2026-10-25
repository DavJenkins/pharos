(() => {
  'use strict';
  const button=document.querySelector('#source-check-now'),status=document.querySelector('#source-check-status');
  if(!button || !status)return;
  let pollTimer,readyTimer;
  const heading=button.closest('.source-heading'),summary=heading.querySelector('.source-check-summary'),title=heading.querySelector('h2');
  function layout() {
    // Measure intrinsic text widths so wrapping follows the actual timestamp and available space.
    const measure=node=>{const range=document.createRange();range.selectNodeContents(node);return range.getBoundingClientRect().width;};
    heading.classList.toggle('source-heading-stacked',measure(title)+measure(summary)+32+32>heading.clientWidth);
  }
  const resize=new ResizeObserver(layout);resize.observe(heading);resize.observe(summary);
  new MutationObserver(layout).observe(summary,{childList:true,subtree:true,characterData:true});
  if(document.fonts)document.fonts.ready.then(layout);layout();
  function render(data) {
    clearTimeout(pollTimer);clearTimeout(readyTimer);
    const busy=data.state==='checking';
    button.disabled=busy || data.retry_after>0;button.classList.toggle('checking',busy);button.setAttribute('aria-label',busy?'Checking sources':'Check sources now');button.title=busy?'Checking sources…':'Check sources now';
    status.textContent=data.message||'';
    if(data.checked_at) {
      const holder=document.querySelector('#source-check-time'),date=new Date(data.checked_at);
      if(holder && !Number.isNaN(date.getTime())) {
        const time=document.createElement('time');time.setAttribute('data-local-time','');time.dateTime=data.checked_at;time.textContent=date.toLocaleString();holder.replaceChildren(time);
      }
    }
    if(data.assets)for(const span of document.querySelectorAll('[data-source-asset]')) {
      const item=data.assets[span.dataset.sourceAsset];if(!item)continue;
      if(!item.checked_at){span.textContent='Source unchecked';span.hidden=false;continue;}
      span.textContent=item.status==='unavailable'?'Source unavailable':item.status==='unknown'?'Source unknown':'';
      span.hidden=item.status==='available';
    }
    if(typeof updateLocalTimes==='function')updateLocalTimes();
    if(busy)pollTimer=setTimeout(refresh,2000);
    else if(data.retry_after>0)readyTimer=setTimeout(()=>{button.disabled=false;},(data.retry_after+1)*1000);
  }
  async function refresh() {
    try {const response=await fetch('/api/sources/check',{cache:'no-store'});if(!response.ok)throw Error('Source check status is unavailable.');render(await response.json());}
    catch(error){status.textContent=error.message;button.disabled=false;button.classList.remove('checking');button.setAttribute('aria-label','Check sources now');button.title='Check sources now';}
  }
  button.addEventListener('click',async()=>{
    button.disabled=true;status.textContent='Starting source check…';
    try {
      const response=await fetch('/api/sources/check',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}',cache:'no-store'});
      const data=await response.json();if(!response.ok)throw Error(data.detail||'Could not start the check.');render(data);
    }catch(error){status.textContent=error.message;button.disabled=false;}
  });
  refresh();
})();
