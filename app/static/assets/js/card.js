"use strict";
(()=>{
 const el=id=>document.getElementById(id);let busy=false;
 const message=(text,error=false)=>{el('message').textContent=text;el('message').classList.toggle('error',error);};
 el('build').onclick=async()=>{if(busy)return;busy=true;try{await window.ApplianceJobs.action({action:'card_package',library_gib:Number(el('capacity').value),country:el('country').value.trim().toUpperCase()});message('Package queued. No card is being erased or written by this Ark.');}catch(e){message(e.message,true);}finally{busy=false;}};
 el('download').onclick=async()=>{try{const auth=await window.CaretakerAuth.authorization('Download the card preparation package.');const r=await fetch('/api/appliance-jobs/card-download',{headers:{Authorization:auth}});if(!r.ok)throw Error('Package download was not accepted. Check authorization and build status.');const url=URL.createObjectURL(await r.blob()),a=document.createElement('a');a.href=url;a.download='data-ark-card-preparation.zip';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){message(e.message,true);}};
 async function refresh(){try{const r=await fetch('/api/appliance-jobs/card-package',{cache:'no-store'});if(!r.ok)throw Error();const d=await r.json();el('status').textContent=d.phase+' · '+(d.message||'')+(d.bytes?' · '+(d.bytes/1024**2).toFixed(1)+' MiB':'');el('download').hidden=d.phase!=='ready';}catch(e){el('status').textContent='Waiting for the Ark to reconnect…';}}
 refresh();setInterval(refresh,5000);
})();
