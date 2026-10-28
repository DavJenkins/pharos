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
        popup.innerHTML='<div class="support-content"><h2 id="support-email-heading">Compose a support email</h2><p>To: support@dejsoftware.com</p><label>What happened?<textarea id="support-description" maxlength="6000" placeholder="What were you doing, what did you expect, and what happened instead? Include approximately when it happened."></textarea></label><p id="support-build"></p><p class="support-note">The diagnostic report includes system and network details, service health, recent failures and debug logs. It excludes passwords, keys, tokens, household files and board messages. Review it before sharing.</p><button type="button" id="support-collect">Collect diagnostics</button><p id="support-result" role="status" aria-live="polite"></p><details><summary>Review diagnostic report</summary><pre id="support-report">Diagnostics have not been collected.</pre></details><div class="support-actions"><button type="button" id="support-download-report" disabled>Download diagnostics</button><button type="button" id="support-download-email" disabled>Download complete email (.eml)</button><a class="support-mailto" id="support-mailto">Open email app</a></div><p class="support-note">The complete email file contains the report as an attachment. Open or import it in your email app to review and send. A simple email link cannot attach files; if you use Open email app, attach the downloaded diagnostic report yourself. No email is sent automatically.</p></div><div class="support-close-row"><button type="button" id="support-close">Close</button></div>';
        document.body.append(popup);
        popup.querySelector('#support-close').onclick=()=>popup.close();
        popup.querySelector('#support-description').oninput=updateMailto;
        popup.querySelector('#support-collect').onclick=collect;
        popup.querySelector('#support-download-report').onclick=()=>download(JSON.stringify(report,null,2)+'\n','dataark-support-diagnostics.json','application/json');
        popup.querySelector('#support-download-email').onclick=()=>download(emailFile(),'dataark-support.eml','message/rfc822');
        return popup;
    }
    function body(){return (popup.querySelector('#support-description').value.trim()||'[Describe the problem here]')+'\n\nData Ark troubleshooting context\nBuild: '+summary()+'\nPublished: '+published()+'\nCollected: '+(report?.collected_at||'Not collected')+'\n\n'+(report?(report.partial?'Only partial browser/build context is attached. Full system/debug logs were not collected.':'The diagnostic report is attached to the complete email draft.'):'Diagnostics have not been collected.');}
    function updateMailto(){if(popup)popup.querySelector('#support-mailto').href='mailto:'+recipient+'?subject='+encodeURIComponent('Data Ark support — '+(build?.revision||'unknown build').slice(0,12))+'&body='+encodeURIComponent(body());}
    function download(value,name,type){const url=URL.createObjectURL(new Blob([value],{type}));const link=document.createElement('a');link.href=url;link.download=name;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);}
    function base64(value){const bytes=new TextEncoder().encode(value);let raw='';for(const byte of bytes)raw+=String.fromCharCode(byte);return btoa(raw).match(/.{1,76}/g).join('\r\n');}
    function clientContext(){return {browser:navigator.userAgent,language:navigator.language,timezone:Intl.DateTimeFormat().resolvedOptions().timeZone,page:location.origin+location.pathname,last_known_status:typeof DataArkStatus==='undefined'?null:DataArkStatus.data,recent_errors:errors.map(value=>/password|token|secret|authorization/i.test(value)?'[Credential-related error omitted]':value)};}
    function emailFile(){
        const boundary='dataark-support-'+Date.now();
        return ['To: '+recipient,'Subject: Data Ark support','Date: '+new Date().toUTCString(),'X-Unsent: 1','MIME-Version: 1.0','Content-Type: multipart/mixed; boundary="'+boundary+'"','','--'+boundary,'Content-Type: text/plain; charset=UTF-8','Content-Transfer-Encoding: base64','',base64(body()),'--'+boundary,'Content-Type: application/json; name="dataark-support-diagnostics.json"','Content-Disposition: attachment; filename="dataark-support-diagnostics.json"','Content-Transfer-Encoding: base64','',base64(JSON.stringify(report,null,2)),'--'+boundary+'--',''].join('\r\n');
    }
    async function collect(){
        if(busy)return;busy=true;const button=popup.querySelector('#support-collect');button.disabled=true;
        const result=popup.querySelector('#support-result');result.textContent='Collecting a read-only diagnostic snapshot…';
        try{
            const auth=await window.CaretakerAuth.authorization('Collect system and debug details for a support email.');
            const response=await fetch('/api/network/admin/diagnostics',{method:'POST',headers:{'Content-Type':'application/json',Authorization:auth},body:'{}',cache:'no-store',signal:AbortSignal.timeout(145000)});
            window.CaretakerAuth.rejected(response);const value=await response.json();if(!response.ok)throw Error(value.detail||'Diagnostics could not be collected.');
            report={...value.report,build:build||value.report.build,client:clientContext()};
            popup.querySelector('#support-report').textContent=JSON.stringify(report,null,2);
            popup.querySelector('#support-download-report').disabled=false;popup.querySelector('#support-download-email').disabled=false;
            result.textContent='Diagnostics collected. Review the report, then download the complete email draft or attach the report in your email app.';updateMailto();
        }catch(error){
            result.textContent=error.name==='AbortError'?'Collection cancelled.':error.message+' A partial report with browser/build context is available.';
            if(error.name!=='AbortError'){
                report={collected_at:new Date().toISOString(),partial:true,collection_error:error.message,build,client:clientContext()};
                popup.querySelector('#support-report').textContent=JSON.stringify(report,null,2);
                popup.querySelector('#support-download-report').disabled=false;popup.querySelector('#support-download-email').disabled=false;updateMailto();
            }
        }
        finally{busy=false;button.disabled=false;}
    }
    async function open(){
        create();await ready;
        if(!report){
            report={collected_at:new Date().toISOString(),partial:true,collection_error:'Full server diagnostics have not been collected.',build,client:clientContext()};
            popup.querySelector('#support-report').textContent=JSON.stringify(report,null,2);
            popup.querySelector('#support-download-report').disabled=false;popup.querySelector('#support-download-email').disabled=false;
            popup.querySelector('#support-result').textContent='Basic browser/build context is ready. Collect diagnostics to add system details and logs.';
        }
        popup.querySelector('#support-build').textContent='Build: '+summary()+' · Published: '+published();updateMailto();popup.showModal();popup.querySelector('#support-description').focus();
    }
    window.ArkSupportEmail=Object.freeze({open,summary,published,ready});
})();
