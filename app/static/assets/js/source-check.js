(() => {
  'use strict';
  const button=document.querySelector('#source-check-now'),status=document.querySelector('#source-check-status');
  if(!button || !status)return;
  let pollTimer,readyTimer;
  function render(data) {
    clearTimeout(pollTimer);clearTimeout(readyTimer);
    const busy=data.state==='checking';
    button.disabled=busy || data.retry_after>0;button.textContent=busy?'Checking…':'Check now';
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
    catch(error){status.textContent=error.message;button.disabled=false;button.textContent='Check now';}
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
