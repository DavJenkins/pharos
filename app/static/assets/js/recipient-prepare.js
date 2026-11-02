"use strict";
(()=>{
 const el=id=>document.getElementById(id);let plan=null,busy=false;
 function message(t,error=false){el('message').textContent=t;el('message').classList.toggle('error',error);}
 function sheet(html){const blob=new Blob([html],{type:'text/html;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='your-private-data-ark-welcome.html';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
 async function task(fn){if(busy)return;busy=true;try{await fn();}catch(e){message(e.message,true);}finally{busy=false;}}
 el('inspect').onclick=()=>task(async()=>{plan=await window.ApplianceJobs.action({action:'recipient_preview'});el('layout').textContent=plan.layout+' · '+plan.network_mode;for(const [id,rows] of [['blockers',plan.blockers],['changes',plan.changes]])el(id).replaceChildren(...rows.map(t=>{const li=document.createElement('li');li.textContent=t;return li;}));el('personal').textContent=plan.personal_review;el('prepare').disabled=!plan.eligible;message(plan.eligible?'Review the changes and personal-file checklist before preparing.':'Resolve the listed owner-specific items, then inspect again.',!plan.eligible);});
 el('prepare').onclick=()=>task(async()=>{if(!plan||!el('reviewed').checked)throw Error('Complete the personal-file review first.');if(!confirm('Prepare this appliance for a new owner on its NEXT BOOT? Save the private welcome sheet, then shut down.'))return;window.CaretakerAuth.forget();const d=await window.ApplianceJobs.action({action:'recipient_prepare',plan_id:plan.plan_id,personal_reviewed:true});sheet(d.html);message(d.message);el('prepare').disabled=true;});
 el('sheet').onclick=()=>task(async()=>{const d=await window.ApplianceJobs.action({action:'recipient_sheet'});sheet(d.html);message('Private welcome sheet downloaded. Open it to print or save as PDF.');});
})();
