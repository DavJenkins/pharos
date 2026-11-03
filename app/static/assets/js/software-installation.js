"use strict";
(()=>{
 const get=id=>document.getElementById(id),state=get('installation-state'),result=get('installation-result'),stage=get('installation-stage'),apply=get('installation-apply'),file=get('installation-file'),download=get('installation-download'),progress=get('installation-progress');
 let staged=null,poll=null,selected=null,configured=false,busy=false,seenDownload=null;
 function message(text,error=false){result.textContent=text;result.className=error?'update-feedback update-error':'update-feedback';}
 function downloadButton(){download.hidden=!selected?.download_available;download.disabled=!configured||busy;}
 window.addEventListener('ark-release-checked',event=>{selected=event.detail;downloadButton();});
 const labels={idle:'Ready',queued:'Update queued',preparing:'Preparing rollback snapshot',applying:'Installing software',checking:'Checking updated software',completed:'Software update complete',rolling_back:'Restoring previous software',rolled_back:'Update rolled back; previous software is running',rollback_pending_health:'Previous software restored; health check pending',refused:'Update refused; software retained',interrupted_before_apply:'Update interrupted before software was changed'};
 async function status(){
  try{
   const response=await fetch('/api/software-updates/installation',{cache:'no-store'});if(!response.ok)throw Error();const value=await response.json();
   state.textContent=value.configured?(labels[value.state]||value.state):'Software installation is not configured. A trusted release-signing public key must be enrolled by the administrator.';
   if(value.error)state.textContent+=' '+value.error;
   const installing=['queued','preparing','applying','checking','rolling_back','rollback_pending_health'].includes(value.state);
   const d=value.download||{},downloading=['queued','downloading','verifying'].includes(d.state);
   configured=!!value.configured;busy=installing||downloading;
   stage.disabled=!configured||busy;file.disabled=busy;downloadButton();
   progress.hidden=!downloading;
   if(downloading){
    apply.hidden=true;
    if(d.total_bytes){progress.value=d.percent||0;}else{progress.removeAttribute('value');}
    message(d.message+(d.state==='downloading'?' '+(d.percent||0)+'% · '+((d.downloaded_bytes||0)/1024**2).toFixed(1)+' / '+(d.total_bytes/1024**2).toFixed(1)+' MiB':''));
   }else if(!installing&&d.id&&seenDownload!==d.id&&['verified','failed','interrupted'].includes(d.state)){
    seenDownload=d.id;
    if(d.state==='verified'&&value.installed_release!==d.tag){staged=d.staged;message('Verified '+staged.release+': '+staged.files+' files, '+staged.removals+' removals. Ready to install; running software has not changed.');apply.hidden=false;}
    else if(d.state!=='verified'){message(d.message,true);}
   }
   if(busy&&!poll)poll=setInterval(status,2000);
   if(!busy&&poll){clearInterval(poll);poll=null;}
   return value;
  }catch(_){state.textContent='The Ark may be restarting. Reconnect or reload to see the update outcome.';}
 }
 download.addEventListener('click',async()=>{
  if(!selected?.download_available||busy)return;
  download.disabled=true;stage.disabled=true;apply.hidden=true;staged=null;
  try{
   message('Starting download on the Ark…');
   const d=await post('/api/software-updates/download',JSON.stringify({tag:selected.release.tag,preview:selected.channel==='preview'}),'application/json','Authorize downloading and verifying '+selected.release.tag+'.');
   seenDownload=null;if(!poll)poll=setInterval(status,2000);await status();
  }catch(error){message(error.name==='AbortError'?'Cancelled.':error.message,true);await status();}
 });
 async function post(url,body,type,purpose){
  const authorization=await CaretakerAuth.authorization(purpose);
  const response=await fetch(url,{method:'POST',headers:{Authorization:authorization,'Content-Type':type},body});
  CaretakerAuth.rejected(response);const value=await response.json();if(!response.ok)throw Error(value.detail||'Software operation failed.');return value;
 }
 stage.addEventListener('click',async()=>{
  if(!file.files[0]){message('Choose a signed software update package first.',true);return;}
  if(file.files[0].size>256*1024*1024){message('Package exceeds 256 MiB.',true);return;}
  stage.disabled=true;apply.hidden=true;staged=null;
  try{message('Verifying and staging…');staged=await post('/api/software-updates/stage',file.files[0],'application/gzip','Authorize verification of this software package.');message('Verified '+staged.release+': '+staged.files+' files, '+staged.removals+' removals. The Ark has not been changed.');apply.hidden=false;}
  catch(error){message(error.name==='AbortError'?'Cancelled.':error.message,true);}finally{await status();}
 });
 file.addEventListener('change',()=>{staged=null;apply.hidden=true;result.textContent='';});
 apply.addEventListener('click',async()=>{
  if(!staged||!confirm('Install '+staged.release+'? The Ark API will restart. Configuration and content are retained; failed health checks trigger rollback.'))return;
  apply.disabled=true;
  try{await post('/api/software-updates/install',JSON.stringify({id:staged.id}),'application/json','Authorize installation of '+staged.release+'.');result.textContent='Update queued. This page will reconnect after the API restarts.';apply.hidden=true;staged=null;if(!poll)poll=setInterval(status,2000);await status();}
  catch(error){message(error.name==='AbortError'?'Cancelled.':error.message,true);}finally{apply.disabled=false;}
 });
 status();
})();
