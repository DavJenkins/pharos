"use strict";
(()=>{
 const el=id=>document.getElementById(id);let plan=null,running=false;
 function message(text,error=false){el('message').textContent=text;el('message').classList.toggle('error',error);}
 async function action(data){
  const auth=await window.CaretakerAuth.authorization('Authorize the external library transition.');
  if(!auth)throw new Error('Cancelled. No storage change requested.');
  const r=await fetch('/api/external-library/action',{method:'POST',headers:{'Content-Type':'application/json',Authorization:auth},body:JSON.stringify(data)});
  const d=await r.json();if(!r.ok){if(r.status===401)window.CaretakerAuth.forget();throw new Error(d.detail||'Storage request failed');}return d;
 }
 async function task(fn){if(running)return;running=true;try{await fn();}catch(e){message(e.message,true);}finally{running=false;}}
 async function refresh(){try{const r=await fetch('/api/external-library/status',{cache:'no-store'});if(!r.ok)throw new Error();const d=await r.json();message((d.message||d.phase)+(d.percent!=null?' '+d.percent+'%':''),d.phase==='failed');el('switch').hidden=d.phase!=='verified';if(d.plan_id)plan={plan_id:d.plan_id};}catch(e){message('Waiting for the Ark to reconnect. The last verified system-card library is retained.');}}
 el('drives').onclick=()=>task(async()=>{const d=await action({action:'drives'});el('drive').replaceChildren();for(const drive of d.drives){const o=document.createElement('option');o.value=drive.uuid;o.textContent=drive.model+' · '+(drive.bytes/1024**3).toFixed(1)+' GiB · '+drive.filesystem+' · '+drive.uuid;el('drive').append(o);}plan=null;el('review').hidden=true;message(d.drives.length?'Choose a drive, then preview.':'No eligible formatted USB drive found.');});
 el('drive').onchange=()=>{plan=null;el('review').hidden=true;};
 el('preview').onclick=()=>task(async()=>{plan=await action({action:'plan',uuid:el('drive').value});el('plan').textContent=plan.files+' files · '+(plan.bytes/1024**3).toFixed(2)+' GiB to copy · '+(plan.free_bytes/1024**3).toFixed(2)+' GiB free on destination.';el('review').hidden=false;message('Review the destination before starting.');});
 el('copy').onclick=()=>task(async()=>{if(!plan)throw new Error('Preview the drive first.');await action({action:'copy',plan_id:plan.plan_id});message('Copy queued. Progress will appear here.');});
 el('switch').onclick=()=>task(async()=>{if(!plan)throw new Error('Refresh the verified plan first.');await action({action:'switch',plan_id:plan.plan_id});message('Switch queued. Waiting for the Ark to reconnect.');});
 el('refresh').onclick=refresh;refresh();setInterval(refresh,5000);
})();
