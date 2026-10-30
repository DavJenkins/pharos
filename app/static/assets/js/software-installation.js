"use strict";
(()=>{
 const get=id=>document.getElementById(id),state=get('installation-state'),result=get('installation-result'),stage=get('installation-stage'),apply=get('installation-apply'),file=get('installation-file');
 let staged=null,poll=null;
 const labels={idle:'Ready',queued:'Update queued',preparing:'Preparing rollback snapshot',applying:'Installing software',checking:'Checking updated software',completed:'Software update complete',rolling_back:'Restoring previous software',rolled_back:'Update rolled back; previous software is running',rollback_pending_health:'Previous software restored; health check pending',refused:'Update refused; software retained',interrupted_before_apply:'Update interrupted before software was changed'};
 async function status(){
  try{
   const response=await fetch('/api/software-updates/installation',{cache:'no-store'});if(!response.ok)throw Error();const value=await response.json();
   state.textContent=value.configured?(labels[value.state]||value.state):'Software installation is not configured. A trusted release-signing public key must be enrolled by the administrator.';
   if(value.error)state.textContent+=' '+value.error;
   const busy=['queued','preparing','applying','checking','rolling_back','rollback_pending_health'].includes(value.state);
   stage.disabled=!value.configured||busy;file.disabled=busy;
   if(busy&&!poll)poll=setInterval(status,2000);
   if(!busy&&poll){clearInterval(poll);poll=null;}
   return value;
  }catch(_){state.textContent='The Ark may be restarting. Reconnect or reload to see the update outcome.';}
 }
 async function post(url,body,type,purpose){
  const authorization=await CaretakerAuth.authorization(purpose);
  const response=await fetch(url,{method:'POST',headers:{Authorization:authorization,'Content-Type':type},body});
  CaretakerAuth.rejected(response);const value=await response.json();if(!response.ok)throw Error(value.detail||'Software operation failed.');return value;
 }
 stage.addEventListener('click',async()=>{
  if(!file.files[0]){result.textContent='Choose a signed software update package first.';return;}
  if(file.files[0].size>256*1024*1024){result.textContent='Package exceeds 256 MiB.';return;}
  stage.disabled=true;apply.hidden=true;staged=null;
  try{result.textContent='Verifying and staging…';staged=await post('/api/software-updates/stage',file.files[0],'application/gzip','Authorize verification of this software package.');result.textContent='Verified '+staged.release+': '+staged.files+' files, '+staged.removals+' removals. The Ark has not been changed.';apply.hidden=false;}
  catch(error){result.textContent=error.name==='AbortError'?'Cancelled.':error.message;}finally{await status();}
 });
 file.addEventListener('change',()=>{staged=null;apply.hidden=true;result.textContent='';});
 apply.addEventListener('click',async()=>{
  if(!staged||!confirm('Install '+staged.release+'? The Ark API will restart. Configuration and content are retained; failed health checks trigger rollback.'))return;
  apply.disabled=true;
  try{await post('/api/software-updates/install',JSON.stringify({id:staged.id}),'application/json','Authorize installation of '+staged.release+'.');result.textContent='Update queued. This page will reconnect after the API restarts.';apply.hidden=true;staged=null;if(!poll)poll=setInterval(status,2000);await status();}
  catch(error){result.textContent=error.name==='AbortError'?'Cancelled.':error.message;}finally{apply.disabled=false;}
 });
 status();
})();
