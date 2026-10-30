"use strict";
(()=>{
 const byId=id=>document.getElementById(id),button=byId('update-check'),result=byId('update-result'),link=byId('update-release');
 const date=value=>value?new Date(value).toLocaleString():"—";
 function build(value){byId('update-revision').textContent=value.revision||'—';byId('update-branch').textContent=value.branch||'—';byId('update-published').textContent=date(value.published_at);}
 fetch('/api/software-updates',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error();return r.json();}).then(v=>build(v.installed)).catch(()=>{result.textContent='Build information could not be loaded. Reconnect to the Ark and try again.';});
 button.addEventListener('click',async()=>{
  button.disabled=true;link.hidden=true;result.textContent='Checking official software releases…';
  try{
   const response=await fetch('/api/software-updates/check?preview='+byId('update-preview').checked,{method:'POST',cache:'no-store',signal:AbortSignal.timeout(20000)});
   if(!response.ok)throw Error();const value=await response.json();build(value.installed);byId('update-checked').textContent=date(value.checked_at);result.textContent=value.message;
   if(value.release){link.href=value.release.url;link.textContent='Review '+value.release.tag+(value.release.preview?' (preview)':'')+' ↗';link.hidden=false;}
   if(value.previous_check?.checked_at)result.textContent+=' Previous check: '+date(value.previous_check.checked_at)+'.';
  }catch(_){result.textContent='Could not complete the check. Reconnect to the Ark and try again; no software has been changed.';}
  finally{button.disabled=false;}
 });
})();
