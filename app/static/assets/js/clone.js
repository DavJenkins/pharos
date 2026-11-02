"use strict";
(()=>{
 const $=id=>document.getElementById(id),size=n=>(n/1073741824).toFixed(2)+' GiB';let drives=[],review=null,busy=false,completedUuid=null;
 const act=data=>window.ApplianceJobs.action(data);
 function message(text,error=false){$('message').textContent=text;$('message').classList.toggle('error',error);}
 async function task(fn){if(busy)return;busy=true;try{await fn();}catch(e){message(e.message,true);}finally{busy=false;}}
 function changed(){review=null;$('plan').hidden=true;const d=drives.find(d=>d.uuid===$('drive').value);$('drive-details').textContent=d?[d.model,d.filesystem,d.uuid,...d.mounts].filter(Boolean).join(' · '):'Find an attached empty formatted drive.';$('preview').disabled=!d;}
 $('reload').onclick=()=>task(async()=>{drives=(await act({action:'discover'})).drives;$('drive').replaceChildren(...drives.map(d=>{const o=document.createElement('option');o.value=d.uuid;o.textContent=(d.model||d.device)+' · '+size(d.bytes)+' · '+d.uuid;return o;}));changed();message(drives.length?'Choose a destination and what to include.':'No eligible USB drive found. Connect an empty formatted drive.');});
 $('preview').onclick=()=>task(async()=>{message('Inspecting files and destination capacity…');review=await act({action:'clone_preview',uuid:$('drive').value,mode:$('mode').value});$('capacity').textContent=review.target.path+' · '+review.target.uuid+' · '+size(review.content_bytes)+' content + '+size(review.kit_bytes)+' software allowance + '+size(review.reserve_bytes)+' reserve. '+(review.fits?'Fits.':'Does not fit.');
  for(const [id,rows] of [['included',['Public configuration and setup software',...review.selected.map(x=>x.title+' — '+size(x.bytes))]],['skipped',review.skipped.map(x=>x.title+' — '+x.reason)]]){$(id).replaceChildren(...rows.map(t=>{const li=document.createElement('li');li.textContent=t;return li;}));}
  $('command').textContent=review.command;$('start').disabled=!review.fits;$('start').textContent=review.resuming?'Resume verified copy':'Start verified copy';$('plan').hidden=false;message('Review only. No content was copied. The destination may have been mounted for inspection.');});
 $('start').onclick=()=>task(async()=>{if(!review||!review.fits)throw Error('Preview a plan that fits first.');await act({action:'clone_start',plan_id:review.plan_id});message('Copy queued. You can leave this page; progress is saved on the Ark.');await progress();});
 $('pause').onclick=()=>task(async()=>{const d=await act({action:'clone_pause'});message(d.message);await progress();});
 $('eject').onclick=()=>task(async()=>{const d=await act({action:'clone_eject',uuid:completedUuid});message(d.message);await progress();});
 $('drive').onchange=changed;$('mode').onchange=changed;
 async function progress(){try{const r=await fetch('/api/clone/status',{cache:'no-store'});if(!r.ok)throw Error();const d=await r.json();$('progress').textContent=d.state==='idle'?'No copy is running.':d.state+' · '+(d.files_complete||0)+'/'+(d.files_total||0)+' files'+(d.current?' · '+d.current:'')+(d.error?' · '+d.error:'');$('pause').hidden=!['queued','preparing','copying'].includes(d.state);$('complete').hidden=!['ready','ejected'].includes(d.state);completedUuid=d.target_uuid;$('eject').disabled=d.state!=='ready';if(d.state==='ejected')$('progress').textContent='Drive safely unmounted. You can disconnect it.';}catch(e){$('progress').textContent='Waiting for the Ark to reconnect…';}}
 $('preview').disabled=true;progress();setInterval(progress,5000);
})();
