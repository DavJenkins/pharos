"use strict";
function arkCompactHealth(data, fresh, refreshing) {
 const status=data?.status, health=status?.health;
 const problems=health?.problems?.length?health.problems:(status?.issues||[]).map(message=>({id:'system',message}));
 if(!fresh||!refreshing||!health||!['ok','warning','error'].includes(health.state))return {tone:'gray',count:0,problems:[]};
 const tone=health.state==='error'||status.state==='error'?'red':health.state==='warning'||status.state==='degraded'||problems.length?'amber':'green';
 return {tone,count:tone==='green'?0:Math.max(1,problems.length),problems};
}
function arkStatusWorking(data) {
 const status=data?.status, phase=status?.update?.state;
 return !!(phase&&!['idle','error','failed','completed','cancelled'].includes(phase))||/^(syncing|downloading|verifying|activating|publishing|waiting|queued)/i.test(status?.sync||'');
}
(() => {
 const panel=document.querySelector('.status-bar'),settings=document.getElementById('ark-settings');
 if(!panel||!settings)return;
 const startedAt=Date.now();
 const gear=settings.querySelector('summary');let idleSince=null,lastRefresh=null,attentionUntil=0,lastKey='';
 const badge=document.createElement('span');badge.className='status-attention-count';badge.setAttribute('aria-hidden','true');badge.hidden=true;gear.append(badge);
 const attention=document.createElement('section');attention.className='status-attention';attention.hidden=true;settings.before(attention);
 function update(){
  const now=Date.now(),fresh=lastRefresh!==null&&now-lastRefresh<=(Dashboard.refreshIntervalSeconds+10)*1000;
  const data=DataArkStatus.data,health=arkCompactHealth(data,fresh,Dashboard.refreshEnabled);
  attention.dataset.tone=health.tone;
  const key=JSON.stringify([health.tone,health.problems,Dashboard.refreshEnabled,lastRefresh===null]);
  if(key!==lastKey){
   attentionUntil=now+30000;lastKey=key;attention.replaceChildren();
   if(health.tone!=='green'){
    const heading=document.createElement('strong');heading.textContent=health.tone==='gray'?(!Dashboard.refreshEnabled?'Status updates paused':lastRefresh===null?'Connecting to the Ark…':'Status updates delayed'):'Needs attention';attention.append(heading);
    const list=document.createElement('ul');
    for(const problem of health.problems){
     const row=document.createElement('li'),link=document.createElement('a');
     link.textContent=problem.message;
     link.href=/^content\.(browser_reviews|source_checks|source_changes)$/.test(problem.id)?'/capture.html':problem.id.startsWith('content.')?'/library.html':problem.id.startsWith('https.')?'/config/https.html':problem.id.startsWith('software.')?'/config/updates.html':'/';
     if(problem.id.startsWith('system.')||problem.id==='system'||problem.id.startsWith('service')){link.href='#';link.addEventListener('click',event=>{event.preventDefault();document.getElementById('system-button').click();});}
     row.append(link);list.append(row);
    }
    if(!health.problems.length){
     const row=document.createElement('li');
     if(health.tone==='gray'){
      row.textContent=!Dashboard.refreshEnabled?'Automatic updates are paused.':lastRefresh===null?'Checking the connection automatically…':'The last status is out of date. Retrying automatically…';
      const button=document.createElement('button');button.type='button';button.textContent='Check now';button.addEventListener('click',async()=>{button.disabled=true;try{await Dashboard.refresh();}finally{button.disabled=false;}});row.append(button);
     }else{const link=document.createElement('a');link.href='#';link.textContent='Open System details';link.addEventListener('click',event=>{event.preventDefault();document.getElementById('system-button').click();});row.append(link);}
     list.append(row);
    }
    attention.append(list);
   }
  }
  const idle=!settings.open&&!arkStatusWorking(data);
  if(!idle)idleSince=null;else if(idleSince===null)idleSince=now;
  const compact=idle&&now-idleSince>=30000&&now>=attentionUntil;
  panel.classList.toggle('status-condensed',compact);gear.dataset.health=health.tone;
  badge.hidden=!health.count;badge.textContent=health.count>99?'99+':String(health.count);
  const label=health.tone==='green'?'Healthy':health.tone==='gray'?(!Dashboard.refreshEnabled?'Status updates paused':lastRefresh===null?'Connecting to the Ark':'Status updates delayed'):(health.tone==='red'?'Failure':'Warning')+' - '+health.count+' '+(health.count===1?'item needs':'items need')+' attention';
  gear.title=label+' - Settings';gear.setAttribute('aria-label',gear.title);
  attention.hidden=compact||health.tone==='green'||(health.tone==='gray'&&(now-startedAt<15000||!Dashboard.refreshEnabled)&&!settings.open);
 }
 window.addEventListener('dataark:dashboard-refreshed',()=>{lastRefresh=Date.now();update();});
 window.addEventListener('dataark:connectivity-refreshed',update);
 settings.addEventListener('toggle',()=>{idleSince=null;update();});
 update();setInterval(update,1000);
})();

