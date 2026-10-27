"use strict";
(() => {
 const el = id => document.getElementById(id);
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
    button.onclick=()=>{el("preview").hidden=false;el("preset-title").textContent=p.preset+" — "+p.packages+" packages";el("first").textContent="First packages: "+(p.first_packages.join(", ")||"None");el("commands").textContent="cd /opt/dataark\nsudo venv/bin/python tools/recovery_queue.py create --preset "+p.preset+" --accept-plan "+p.plan_id+"\nsudo systemctl start dataark-recovery.service\n\n# Pause / cancel without removing completed content:\nsudo venv/bin/python tools/recovery_queue.py pause\nsudo venv/bin/python tools/recovery_queue.py cancel\n# Resume: start dataark-recovery.service again.";};td.append(button);tr.append(td);el("presets").append(tr);
   }
  }catch(e){el("plan-message").textContent=e.message;}
 }
 let busy=false;
 async function progress(){if(busy)return;busy=true;try{const q=await request("/api/recovery/status");el("queue").textContent=q.status.replaceAll("_"," ")+" · "+q.completed+" / "+q.total+" packages complete"+(q.message?" · "+q.message:"");el("packages").replaceChildren(...q.jobs.map(p=>{const li=document.createElement("li");li.textContent=p.title+" — "+p.status+(p.partial_bytes?" · "+size(p.partial_bytes)+" downloaded":"")+(p.error?" · "+p.error:"");if(p.path){const a=document.createElement("a");a.href="/library-files/"+p.path.split("/").map(encodeURIComponent).join("/");a.textContent=" Open restored content";li.append(a);}return li;}));}catch(e){el("queue").textContent=e.message;}finally{busy=false;}}
 plans();progress();setInterval(progress,5000);
})();
