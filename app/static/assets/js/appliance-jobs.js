"use strict";
window.ApplianceJobs={async action(data){
 const authorization=await window.CaretakerAuth.authorization('Authorize this Ark copy or restoration action.');
 if(!authorization)throw Error('Cancelled. No operation requested.');
 const r=await fetch('/api/appliance-jobs/action',{method:'POST',headers:{'Content-Type':'application/json',Authorization:authorization},body:JSON.stringify(data)});
 const d=await r.json();if(!r.ok){if(r.status===401)window.CaretakerAuth.forget();throw Error(d.detail||'Request failed');}return d;
}};
