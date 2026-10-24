let refreshing=false, refreshAgain=false;
async function loadCapture() {
 if(refreshing){refreshAgain=true;return;}refreshing=true;
 try {
  const targets=await (await fetch('/assets/downloads/capture-targets.json',{cache:'no-store'})).json();
  const folders=[...new Set(targets.map(x=>x.collection))];const inventories={};
  for (const folder of folders) inventories[folder]=await (await fetch('/library-files/'+folder+'/sources.json',{cache:'no-store'})).json();
  let checks={};try{const response=await fetch('/library-files/browser-capture-status.json',{cache:'no-store'});if(response.ok)checks=await response.json();}catch(_){}
  const root=document.querySelector('#items');root.replaceChildren();
  const pending=document.createElement('div'),installed=document.createElement('details');
  const summary=document.createElement('summary');installed.append(summary);let installedCount=0,pendingCount=0;
  for (const item of targets) {
   const record=inventories[item.collection].find(x=>x.id===item.id);
   const present=record?.status==='installed';const check=checks[item.id];
   const actionNeeded=present && check?.installed_sha256===record.sha256 && (check.state==='changed'||['blocked','unknown'].includes(check.state)&&check.review_due);
   const section=document.createElement('section');const h=document.createElement('h2');h.textContent=item.title;section.append(h);
   const explanation=document.createElement('p');
   explanation.textContent=present?(check?.installed_sha256===record.sha256?check.message:'Installed; no current publisher comparison recorded.'):'Not installed.';
   if(check?.checked_at && present)explanation.textContent+=' Last checked '+new Date(check.checked_at).toLocaleString()+'.';section.append(explanation);
   const button=document.createElement('button');button.dataset.captureId=item.id;
   button.textContent=present?(check?.state==='changed'?'Capture reviewed replacement':'Compare browser copy'):'Download & import';
   if(present)button.dataset.expectedHash=record.sha256;section.append(button);
   const link=document.createElement('a');link.href=item.url;link.target='_blank';link.rel='noopener';link.dataset.armId=item.id;if(present)link.dataset.expectedHash=record.sha256;link.textContent='Open publisher';section.append(link);
   if(present){const local=document.createElement('a');local.href='/library-files/'+item.collection+'/'+record.filename;local.textContent=' · Read installed copy';section.append(local);}
   const status=document.createElement('p');status.setAttribute('role','status');section.append(status);
   if(!present||actionNeeded){pending.append(section);pendingCount++;}else installed.append(section);
   if(present)installedCount++;
  }
  summary.textContent='Installed captures ('+installedCount+') — optional browser comparisons';
  const heading=document.createElement('h2');heading.textContent='Needs capture or review ('+pendingCount+')';root.append(heading);
  if(!pendingCount){const p=document.createElement('p');p.textContent='No capture or update review is pending.';pending.append(p);}
  root.append(pending,installed);
 } catch(e){document.querySelector('#error').textContent='Could not read the current Ark inventory: '+e.message;}
 finally{refreshing=false;if(refreshAgain){refreshAgain=false;loadCapture();}}
}
document.addEventListener('ark-capture-refresh',loadCapture);
loadCapture();
setTimeout(()=>{document.querySelector('#connection').textContent=document.documentElement.dataset.arkCapture==='ready'?'Capture extension connected.':'Extension not connected. Use Chrome and follow the one-time setup instructions.';},1000);
