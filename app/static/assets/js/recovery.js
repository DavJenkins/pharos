"use strict";
(() => {
 const el = id => document.getElementById(id);
 let reviewed=null,queueState=null,acting=false;
 const message=(text,error=false)=>{el("action-message").textContent=text;el("action-message").classList.toggle("error",error);};
 async function action(data){if(acting)return;acting=true;try{const d=await window.ApplianceJobs.action(data);message(d.message||"Request accepted. Progress is saved on the Ark.");await progress();}catch(e){message(e.message,true);}finally{acting=false;}}
 const size = n => n == null ? "Unknown" : (n / 1073741824).toFixed(2) + " GiB";
 const request = async path => { const r = await fetch(path, {cache:"no-store"}); if(!r.ok) throw Error("Recovery information is unavailable. Check the saved profile in the caretaker terminal."); return r.json(); };
 async function plans() {
  try {
   const data = await request("/api/recovery/presets");
   el("plan-message").textContent = "Suggested: " + data.suggested + ". Choose explicitly; nothing is accepted automatically.";
   for(const p of data.presets) {
    const tr=document.createElement("tr");
    const fit=p.capacity.fits ? "Fits" : p.capacity.unknown_packages.length ? "Unknown package sizes" : "Insufficient space";
    for(const text of [p.preset,p.packages,size(p.capacity.required_free_bytes),fit]) {const td=document.createElement("td");td.textContent=text;tr.append(td);}
    const td=document.createElement("td"), button=document.createElement("button");button.type="button";button.textContent="Review";button.disabled=!p.capacity.fits;
    button.onclick=()=>{reviewed=p;el("replace-finished").checked=false;el("replace-label").hidden=!queueState||!["complete","cancelled"].includes(queueState.status);el("preview").hidden=false;el("preset-title").textContent=p.preset+" — "+p.packages+" packages";el("first").textContent="First packages: "+(p.first_packages.join(", ")||"None");el("commands").textContent="cd /opt/dataark\nsudo venv/bin/python tools/recovery_queue.py create --preset "+p.preset+" --accept-plan "+p.plan_id+"\nsudo systemctl start dataark-recovery.service\n\n# Pause / cancel without removing completed content:\nsudo venv/bin/python tools/recovery_queue.py pause\nsudo venv/bin/python tools/recovery_queue.py cancel\n# Resume: start dataark-recovery.service again.";};td.append(button);tr.append(td);el("presets").append(tr);
   }
  }catch(e){el("plan-message").textContent=e.message;}
 }
 let busy=false;
 async function progress(){if(busy)return;busy=true;try{const q=await request("/api/recovery/status");queueState=q;el("restore-pause").hidden=!q.worker_active;el("restore-resume").hidden=q.worker_active||["complete","not_started"].includes(q.status);el("restore-cancel").hidden=["complete","not_started","cancelled"].includes(q.status);el("replace-label").hidden=!["complete","cancelled"].includes(q.status);el("queue").textContent=q.status.replaceAll("_"," ")+" · "+q.completed+" / "+q.total+" packages complete"+(q.message?" · "+q.message:"");el("packages").replaceChildren(...q.jobs.map(p=>{const li=document.createElement("li");li.textContent=p.title+" — "+p.status+(p.partial_bytes?" · "+size(p.partial_bytes)+" downloaded":"")+(p.error?" · "+p.error:"");if(p.path){const a=document.createElement("a");a.href="/library-files/"+p.path.split("/").map(encodeURIComponent).join("/");a.textContent=" Open restored content";li.append(a);}return li;}));}catch(e){el("queue").textContent=e.message;}finally{busy=false;}}
 el("restore-start").onclick=()=>{if(!reviewed)return;action({action:"restore_start",preset:reviewed.preset,plan_id:reviewed.plan_id,replace_finished:el("replace-finished").checked});};
 for(const key of ["pause","resume","cancel"])el("restore-"+key).onclick=()=>{if(key==="cancel"&&!confirm("Cancel this restoration? Verified content and partial files will be retained."))return;action({action:"restore_"+key});};
 plans();progress();setInterval(progress,5000);
})();
