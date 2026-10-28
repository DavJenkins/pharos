/* Support mail is composed locally. Nothing is sent by the Ark. */
(() => {
    "use strict";
    const recipient="support@dejsoftware.com";
    let build=null, popup, report=null, busy=false;
    const errors=[];
    window.addEventListener('error',event=>{errors.push(String(event.message||'Browser error').slice(0,500));if(errors.length>20)errors.shift();});
    window.addEventListener('unhandledrejection',event=>{errors.push(String(event.reason?.message||event.reason||'Unhandled browser error').slice(0,500));if(errors.length>20)errors.shift();});
    const ready=fetch('/assets/build-info.json',{cache:'no-store'}).then(r=>r.ok?r.json():null).then(value=>{build=value;window.dispatchEvent(new Event('ark-build-ready'));return value;}).catch(()=>null);
    function summary(){return build?[(build.revision||'Uncommitted').slice(0,12),build.branch||'', 'source '+build.source_fingerprint.slice(0,12)].filter(Boolean).join(' · '):'—';}
    function published(){return build?.published_at?new Date(build.published_at).toLocaleString():'—';}
    function create(){
        if(popup)return popup;
        popup=document.createElement('dialog');popup.id='support-email-dialog';popup.setAttribute('aria-labelledby','support-email-heading');
        popup.innerHTML=`<div class="support-content">
<h2 id="support-email-heading">Email Data Ark support</h2>
<p class="support-intro">Prepare a message to <strong>support@dejsoftware.com</strong>. You will review and send it in your own email app.</p>
<section class="support-step" aria-labelledby="support-step-one"><h3 id="support-step-one">1. Describe the problem</h3>
<label for="support-description">What happened?</label><textarea id="support-description" maxlength="6000" placeholder="What were you doing? What did you expect? What happened instead, and approximately when?"></textarea></section>
<section class="support-step" aria-labelledby="support-step-two"><h3 id="support-step-two">2. Add diagnostics</h3>
<p class="support-note">Recommended: include system details and recent debug logs. This may ask for the caretaker password.</p>
<button type="button" id="support-collect">Add system diagnostics</button>
<p id="support-result" role="status" aria-live="polite"></p>
<details><summary>Review what will be shared</summary><p class="support-note">The report includes system and network details, service health, recent failures and available debug logs. Passwords, keys, tokens, household files and board messages are excluded. Review technical details before sharing.</p><p id="support-build"></p><pre id="support-report">Diagnostics have not been collected.</pre></details></section>
<section class="support-step" aria-labelledby="support-step-three"><h3 id="support-step-three">3. Open your email draft and attach the report</h3>
<p>First save the report. Then open the addressed email draft, attach <strong>dataark-support-diagnostics.json</strong> from your downloads, and send it.</p>
<div class="support-actions"><button type="button" id="support-download-report" disabled>Save diagnostics attachment</button><a class="support-mailto" id="support-mailto">Open email draft</a></div>
<p id="support-delivery" class="support-note" role="status" aria-live="polite">The email link cannot attach the file for you. Nothing is sent automatically.</p>
<details class="support-alternative"><summary>Other ways to send</summary><p>If you use webmail, create a message to support@dejsoftware.com, describe the problem, and attach the saved report.</p><p>Some desktop email apps can open or import a complete draft with the attachment included:</p><button type="button" id="support-download-email" disabled>Save complete email draft (.eml)</button><p class="support-note">Opening an .eml file may show a saved message rather than a new draft, depending on the email app. You still need to review and send it. You can also keep the file and send it when you have internet access.</p></details></section>
</div><div class="support-close-row"><button type="button" id="support-close">Close</button></div>`;
        document.body.append(popup);
        popup.querySelector('#support-close').onclick=()=>popup.close();
        popup.querySelector('#support-description').oninput=updateMailto;
        popup.querySelector('#support-collect').onclick=collect;
        popup.querySelector('#support-download-report').onclick=()=>{if(busy)return;download(JSON.stringify(report,null,2)+'\n','dataark-support-diagnostics.json','application/json');popup.querySelector('#support-delivery').textContent='Download started: dataark-support-diagnostics.json. Next, open the email draft and attach that file from your downloads.';};
        popup.querySelector('#support-mailto').onclick=event=>{if(busy){event.preventDefault();return;}popup.querySelector('#support-delivery').textContent='Your email app has been requested. Attach dataark-support-diagnostics.json, review the message, and press Send in your email app. If nothing opens, use Other ways to send below.';};
        popup.querySelector('#support-download-email').onclick=()=>download(emailFile(),'dataark-support.eml','message/rfc822');
        return popup;
    }
    function body(attached=false){return (popup.querySelector('#support-description').value.trim()||'[Describe the problem here]')+'\n\nData Ark troubleshooting context\nBuild: '+summary()+'\nPublished: '+published()+'\nCollected: '+(report?.collected_at||'Not collected')+'\n\n'+(report?((report.partial?'The report contains basic browser/build context only; full system/debug logs were not collected.':'The report contains system details and available debug logs.')+'\n'+(attached?'Attached: dataark-support-diagnostics.json.':'Please attach dataark-support-diagnostics.json from your downloads before sending.')):'Diagnostics have not been collected.');}
    function updateMailto(){if(popup)popup.querySelector('#support-mailto').href='mailto:'+recipient+'?subject='+encodeURIComponent('Data Ark support — '+(build?.revision||'unknown build').slice(0,12))+'&body='+encodeURIComponent(body());}
    function download(value,name,type){const url=URL.createObjectURL(new Blob([value],{type}));const link=document.createElement('a');link.href=url;link.download=name;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);}
    function base64(value){const bytes=new TextEncoder().encode(value);let raw='';for(const byte of bytes)raw+=String.fromCharCode(byte);return btoa(raw).match(/.{1,76}/g).join('\r\n');}
    function clientContext(){return {browser:navigator.userAgent,language:navigator.language,timezone:Intl.DateTimeFormat().resolvedOptions().timeZone,page:location.origin+location.pathname,last_known_status:typeof DataArkStatus==='undefined'?null:DataArkStatus.data,recent_errors:errors.map(value=>/password|token|secret|authorization/i.test(value)?'[Credential-related error omitted]':value)};}
    function emailFile(){
        const boundary='dataark-support-'+Date.now();
        return ['To: '+recipient,'Subject: Data Ark support','Date: '+new Date().toUTCString(),'X-Unsent: 1','MIME-Version: 1.0','Content-Type: multipart/mixed; boundary="'+boundary+'"','','--'+boundary,'Content-Type: text/plain; charset=UTF-8','Content-Transfer-Encoding: base64','',base64(body(true)),'--'+boundary,'Content-Type: application/json; name="dataark-support-diagnostics.json"','Content-Disposition: attachment; filename="dataark-support-diagnostics.json"','Content-Transfer-Encoding: base64','',base64(JSON.stringify(report,null,2)),'--'+boundary+'--',''].join('\r\n');
    }
    async function collect(){
        if(busy)return;busy=true;const button=popup.querySelector('#support-collect');button.disabled=true;
        for(const id of ['#support-download-report','#support-download-email'])popup.querySelector(id).disabled=true;
        popup.querySelector('#support-mailto').setAttribute('aria-disabled','true');
        const result=popup.querySelector('#support-result');result.textContent='Collecting system details and logs. Please wait…';
        try{
            const auth=await window.CaretakerAuth.authorization('Collect system and debug details for a support email.');
            const response=await fetch('/api/network/admin/diagnostics',{method:'POST',headers:{'Content-Type':'application/json',Authorization:auth},body:'{}',cache:'no-store',signal:AbortSignal.timeout(145000)});
            window.CaretakerAuth.rejected(response);const value=await response.json();if(!response.ok)throw Error(value.detail||'Diagnostics could not be collected.');
            report={...value.report,build:build||value.report.build,client:clientContext()};
            popup.querySelector('#support-report').textContent=JSON.stringify(report,null,2);
            popup.querySelector('#support-download-report').disabled=false;popup.querySelector('#support-download-email').disabled=false;
            button.textContent='Refresh system diagnostics';result.textContent='Full diagnostic report ready. Review what will be shared, then continue to step 3.';updateMailto();
        }catch(error){
            result.textContent=error.name==='AbortError'?'Collection cancelled.':error.message+' A partial report with browser/build context is available.';
            if(error.name!=='AbortError'){
                report={collected_at:new Date().toISOString(),partial:true,collection_error:error.message,build,client:clientContext()};
                popup.querySelector('#support-report').textContent=JSON.stringify(report,null,2);
                popup.querySelector('#support-download-report').disabled=false;popup.querySelector('#support-download-email').disabled=false;updateMailto();
            }
        }
        finally{busy=false;button.disabled=false;for(const id of ['#support-download-report','#support-download-email'])popup.querySelector(id).disabled=!report;popup.querySelector('#support-mailto').setAttribute('aria-disabled','false');}
    }
    async function open(){
        create();await ready;
        if(!report){
            report={collected_at:new Date().toISOString(),partial:true,collection_error:'Full server diagnostics have not been collected.',build,client:clientContext()};
            popup.querySelector('#support-report').textContent=JSON.stringify(report,null,2);
            popup.querySelector('#support-download-report').disabled=false;popup.querySelector('#support-download-email').disabled=false;
            popup.querySelector('#support-result').textContent='Basic browser/build report ready. Add system diagnostics to include system details and logs, or continue with the basic report.';
        }
        popup.querySelector('#support-build').textContent='Build: '+summary()+' · Published: '+published();updateMailto();popup.showModal();popup.querySelector('#support-description').focus();
    }
    window.ArkSupportEmail=Object.freeze({open,summary,published,ready});
})();
