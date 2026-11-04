"use strict";
function arkCardProgress(progress,ids,items=[]){
 if(!progress||!['downloading','verifying','activating','publishing','recovering'].includes(progress.state))return null;
 const id=progress.asset_id||items.find(item=>item.title===progress.asset)?.id;
 if(!id||!ids.includes(id))return null;
 const percent=typeof progress.percent==='number'&&Number.isFinite(progress.percent)&&progress.percent>=0&&progress.percent<=100?Math.round(progress.percent):null;
 const stepped=Number.isInteger(progress.step)&&Number.isInteger(progress.total_steps)&&progress.step>=1&&progress.step<=progress.total_steps&&progress.total_steps<=12;
 if(percent===null&&!stepped)return null;
 return {id,percent,phase:progress.phase||progress.label||'Updating content',step:stepped?progress.step:null,total:stepped?progress.total_steps:null,bytes:progress.bytes_processed,totalBytes:progress.total_bytes,remaining:progress.estimated_remaining_seconds};
}
function arkStepSegments(step,total){
 const slice=360/total,gap=Math.min(3,slice/8),parts=[];
 for(let i=0;i<total;i++){
  const color=i<step-1?'#d9b74e':i===step-1?'#168fd0':'#c8d2da';
  parts.push('transparent '+(i*slice)+'deg '+(i*slice+gap)+'deg',color+' '+(i*slice+gap)+'deg '+((i+1)*slice-gap)+'deg','transparent '+((i+1)*slice-gap)+'deg '+((i+1)*slice)+'deg');
 }
 return 'conic-gradient('+parts.join(',')+')';
}

function arkRenderProgressBadge(host,current,onOpen=null){
   let badge=host.querySelector('.manifest-card-progress');
   host.classList.toggle('has-card-progress',!!current);
   if(!current){badge?.remove();return;}
   if(!badge){badge=document.createElement('a');badge.className='manifest-card-progress';for(const name of ['progress-steps','progress-current','progress-caption']){const span=document.createElement('span');span.className=name;badge.append(span);}const caption=badge.querySelector('.progress-caption');caption.append(document.createElement('strong'),document.createElement('small'));host.append(badge);}
   badge.href='/library.html?review=changes&assets='+encodeURIComponent(current.id)+'#library-source-changes';
   badge.onclick=onOpen?event=>{event.preventDefault();onOpen();}:null;
   badge.style.setProperty('--progress-angle',((current.percent||0)*3.6)+'deg');
   badge.querySelector('.progress-steps').hidden=!current.step;
   if(current.step)badge.style.setProperty('--step-segments',arkStepSegments(current.step,current.total));
   badge.classList.toggle('progress-unmeasured',current.percent===null);
   badge.querySelector('strong').textContent=current.percent===null?'…':current.percent+'%';
   const caption=badge.querySelector('small');caption.textContent=current.step?'Step '+current.step+' of '+current.total:'';caption.hidden=!current.step;
   const parts=[current.step?'Step '+current.step+' of '+current.total:null,current.phase,current.percent===null?'Progress not measured':current.percent+'% of this step'];
   if(Number.isFinite(current.bytes)&&current.totalBytes>0)parts.push((current.bytes/1024**3).toFixed(2)+' of '+(current.totalBytes/1024**3).toFixed(2)+' GiB');
   if(Number.isFinite(current.remaining)&&current.remaining>0)parts.push('About '+Math.ceil(current.remaining/60)+' min remaining in this step');
   badge.title=parts.filter(Boolean).join(' — ')+'. Open library progress.';
   badge.setAttribute('aria-label',badge.title);
}
