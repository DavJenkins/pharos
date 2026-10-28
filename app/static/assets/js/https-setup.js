"use strict";
(() => {
    const el=id=>document.getElementById(id);
    const busyPhases=new Set(["requesting","waiting_dns","verifying","installing"]);
    let challenge=null,busy=false;
    function lock(){window.CaretakerAuth.forget();el("https-admin").hidden=true;el("https-lock").hidden=true;el("https-auth-message").textContent="HTTPS setup is locked.";challenge=null;}
    async function authorization(){return window.CaretakerAuth.authorization("Authorize HTTPS setup.");}
    async function request(path,options={}){const r=await fetch(path,{cache:"no-store",...options});const d=await r.json();if(!r.ok){if(r.status===401)window.CaretakerAuth.forget();throw new Error(d.detail||"HTTPS request failed");}return d;}
    const phases={not_configured:"Not configured — optional",requesting:"Requesting DNS verification",waiting_dns:"Waiting for your DNS record",verifying:"Checking public DNS",installing:"Installing certificate",ready:"Ready",failed:"Setup needs attention",cancelled:"Setup cancelled",interrupted:"Setup was interrupted"};
    function render(d){
        el("https-identity").textContent=d.device_id||"Not initialized";
        el("https-state").textContent=phases[d.phase]||d.phase||"Not configured";
        el("https-message").textContent=d.message||(!d.available?"HTTPS setup is not installed yet.":"");
        const cert=d.certificate;
        el("https-certificate").textContent=cert?.expires_at?(d.domain+" — expires "+new Date(cert.expires_at).toLocaleString()+(d.certificate_health==="expired"?" — expired":d.days_remaining!==undefined?" ("+d.days_remaining+" days remaining)":"")):"No public certificate installed";
        const link=el("https-open");link.hidden=!d.enabled||!d.domain;if(d.domain){link.href="https://"+d.domain+"/";link.textContent="Open "+d.domain+" with HTTPS";}
        el("https-start").disabled=busy||busyPhases.has(d.phase);el("https-cancel").disabled=busy||!busyPhases.has(d.phase)||d.phase==="installing";
        if(Object.hasOwn(d,"challenge"))challenge=d.challenge||null;el("https-challenge").hidden=!challenge;
        if(challenge){el("https-dns-name").value=challenge.name;el("https-dns-value").value=challenge.value;el("https-dns-time").textContent="This setup session expires at "+new Date(challenge.expires_at*1000).toLocaleTimeString()+". Keep the record until setup finishes.";el("https-verify").disabled=busy||d.phase!=="waiting_dns";}
        if(!el("https-domain").value&&(d.setup_domain||d.domain))el("https-domain").value=d.setup_domain||d.domain;
    }
    async function refresh(){try{let d=await request("/api/https/status");const remembered=window.CaretakerAuth.cachedAuthorization();if(remembered)d={...d,...await request("/api/https/setup",{headers:{Authorization:remembered}})};render(d);}catch(e){el("https-message").textContent=e.message;}finally{setTimeout(refresh,3000);}}
    async function perform(data){if(busy)return;busy=true;try{const auth=await authorization();const d=await request("/api/https/setup",{method:"POST",headers:{"Content-Type":"application/json",Authorization:auth},body:JSON.stringify(data)});el("https-message").textContent=d.message;const state=await request("/api/https/setup",{headers:{Authorization:auth}});render(state);}catch(e){el("https-message").textContent=e.message;}finally{busy=false;}}
    el("https-unlock-form").addEventListener("submit",async e=>{e.preventDefault();try{const auth=await authorization();const d=await request("/api/https/setup",{headers:{Authorization:auth}});el("https-admin").hidden=false;el("https-lock").hidden=false;el("https-auth-message").textContent="Setup details loaded. Changes request the caretaker password when needed.";render(d);}catch(error){el("https-auth-message").textContent=error.message;}});
    el("https-lock").addEventListener("click",lock);
    el("https-start-form").addEventListener("submit",e=>{e.preventDefault();perform({action:"start",domain:el("https-domain").value,email:el("https-email").value,agree_terms:el("https-terms").checked});});
    el("https-verify").addEventListener("click",()=>{if(challenge)perform({action:"verify",job_id:challenge.job_id,challenge_id:challenge.challenge_id});});
    el("https-cancel").addEventListener("click",()=>perform({action:"cancel"}));
    refresh();
})();
