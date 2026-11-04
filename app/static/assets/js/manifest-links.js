"use strict";
document.querySelectorAll("[data-manifest-kiwix-port]").forEach(link => {
    const destination = new URL(location.href);
    destination.protocol = "http:";
    destination.port = link.dataset.manifestKiwixPort;
    const path = new URL(link.dataset.manifestKiwixPath, destination.origin);
    destination.pathname = path.pathname;
    destination.search = path.search;
    destination.hash = path.hash;
    link.href = destination.href;
});

// Show observation times in the reader's locale and time zone.
function updateLocalTimes() {
document.querySelectorAll("time[data-local-time]").forEach(element => {
    const date = new Date(element.getAttribute("datetime"));
    if (Number.isNaN(date.getTime())) return;
    element.title = new Intl.DateTimeFormat(undefined, {
        dateStyle: "full", timeStyle: "long"
    }).format(date);
    element.textContent = new Intl.DateTimeFormat(undefined, {
        year: "2-digit", month: "numeric", day: "numeric",
        hour: "2-digit", minute: "2-digit"
    }).format(date);
    if (element.closest(".source-check-summary")) {
        const elapsed = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
        const units = [[86400, "day"], [3600, "hour"], [60, "minute"]];
        const unit = units.find(([seconds]) => elapsed >= seconds);
        const age = unit ? Math.floor(elapsed / unit[0]) : 0;
        const relative = unit ? age + " " + unit[1] + (age === 1 ? "" : "s") + " ago" : "just now";
        element.textContent += " (" + relative + ")";
    }
});
}
updateLocalTimes();
setInterval(updateLocalTimes, 60000);

// This is a browser display preference, not a change to the shared catalogue.
(() => {
 const toggle=document.getElementById('installed-sources-only');
 if(!toggle)return;
 const section=toggle.closest('.manifest-category');
 const cards=section.querySelectorAll('.manifest-card[data-installed]');
 toggle.closest('.installed-only-switch').hidden=Array.from(cards).every(card=>card.dataset.installed==='true');
 const defaultOn=toggle.closest('.source-heading').dataset.installedOnlyDefault==='true';
 const key=defaultOn?'dataark.installedSourcesOnly.default-installed':'dataark.installedSourcesOnly';
 toggle.checked=defaultOn;
 try{const saved=localStorage.getItem(key);if(saved!==null)toggle.checked=saved==='true';}catch{}
 const empty=document.createElement('p');empty.className='manifest-empty';
 empty.textContent='No sources are installed yet. Turn off Installed only to explore available sources.';
 empty.hidden=true;section.append(empty);
 function apply(){
  let visible=0;
  cards.forEach(card=>{card.hidden=toggle.checked && card.dataset.installed!=='true';if(!card.hidden)visible++;});
  empty.hidden=!toggle.checked || visible>0;
 }
 toggle.addEventListener('change',()=>{apply();try{localStorage.setItem(key,String(toggle.checked));}catch{}});
 apply();
})();

function arkCardIssues(items,ids){
 const wanted=new Set(ids),groups={changes:new Map(),failures:new Map(),reviews:new Map()};
 for(const item of items){
  if(!wanted.has(item.id))continue;
  const update=item.update||{},key=update.source_url||item.id;
  if(update.pending_change)groups.changes.set(key,item.id);
  if(update.result==='error')groups.failures.set(key,item.id);
  if(update.result==='browser_review_due')groups.reviews.set(key,item.id);
 }
 return Object.fromEntries(Object.entries(groups).map(([kind,values])=>[kind,Array.from(values.values())]));
}
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
(() => {
 function render(){
  const inventory=window.ArkLibraryDiagnostics;
  const progress=typeof DataArkStatus!=='undefined'?DataArkStatus.data?.status?.update:inventory?.progress;
  for(const card of document.querySelectorAll('.manifest-card[data-repository-id]')){
   const ids=Array.from(card.querySelectorAll('[data-source-asset]'),node=>node.dataset.sourceAsset);
   const current=arkCardProgress(progress,ids,inventory?.installed||[]);
   let badge=card.querySelector('.manifest-card-progress');
   card.classList.toggle('has-card-progress',!!current);
   if(!current){badge?.remove();continue;}
   if(!badge){badge=document.createElement('a');badge.className='manifest-card-progress';for(const name of ['progress-steps','progress-current','progress-caption']){const span=document.createElement('span');span.className=name;badge.append(span);}const caption=badge.querySelector('.progress-caption');caption.append(document.createElement('strong'),document.createElement('small'));card.append(badge);}
   badge.href='/library.html?review=changes&assets='+encodeURIComponent(current.id)+'#library-source-changes';
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
 }
 window.addEventListener('dataark:dashboard-refreshed',render);
 window.addEventListener('dataark:library-diagnostics',render);
 render();
})();
(() => {
 function render(){
  const inventory=window.ArkLibraryDiagnostics;if(!inventory||inventory.unavailable)return;
  for(const card of document.querySelectorAll('.manifest-card[data-repository-id]')){
   const ids=Array.from(card.querySelectorAll('[data-source-asset]'),node=>node.dataset.sourceAsset);
   const issues=arkCardIssues(inventory.installed||[],ids);
   let notice=card.querySelector('.manifest-card-diagnostics');
   const count=Object.values(issues).reduce((sum,values)=>sum+values.length,0);
   card.classList.toggle('has-diagnostics',count>0);
   const caretaker=!!window.CaretakerAuth?.isRemembered();
   card.classList.toggle('diagnostics-expanded',caretaker);
   if(!count){notice?.remove();continue;}
   if(!notice){notice=document.createElement('aside');notice.className='manifest-card-diagnostics';card.querySelector('h3').after(notice);}
   notice.replaceChildren();const title=document.createElement('strong');title.textContent='! Needs attention';notice.append(title);
   const icon=document.createElement('a');icon.className='manifest-diagnostic-icon';icon.textContent='!';icon.title='Source needs attention';icon.setAttribute('aria-label','Source needs attention: '+count+' issue'+(count===1?'':'s'));
   const first=issues.changes.length?'changes':issues.failures.length?'failures':'reviews';icon.href=first==='reviews'?'/capture.html':'/library.html?review='+first+'&assets='+encodeURIComponent(issues[first].join(','))+'#library-source-changes';notice.append(icon);
   for(const [kind,label] of [['changes','publisher changes'],['failures','failed checks'],['reviews','browser reviews due']]){
    if(!issues[kind].length)continue;
    const link=document.createElement('a'),n=issues[kind].length;link.textContent=n+' '+(kind==='changes'?'publisher change'+(n===1?'':'s'):kind==='failures'?'failed check'+(n===1?'':'s'):'browser review'+(n===1?'':'s')+' due');
    link.href=kind==='reviews'?'/capture.html':'/library.html?review='+kind+'&assets='+encodeURIComponent(issues[kind].join(','))+'#library-source-changes';
    notice.append(link);
   }
  }
 }
 window.addEventListener('dataark:library-diagnostics',render);window.addEventListener('caretaker-auth-changed',render);setInterval(render,15000);render();
})();
