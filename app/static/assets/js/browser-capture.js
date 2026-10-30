function captureCategory(item,record,check) {
 const present=record?.status==='installed';
 const current=present && check?.installed_sha256===record.sha256;
 if(present && !(current && (check.state==='changed'||(['blocked','unknown'].includes(check.state)&&check.review_due))))return 'Installed — no action needed';
 if(!present && item.source?.disposition==='optional')return 'Optional references';
 if(item.source?.failure_kind==='broken_link')return 'Broken links — repair needed';
 if(present && check?.review_due)return 'Browser review due';
 if(present || item.source?.failure_kind==='access_blocked')return 'Browser check needed';
 return 'Missing files';
}
let refreshing=false, refreshAgain=false;
async function loadCapture() {
 if(refreshing){refreshAgain=true;return;}refreshing=true;
 try {
  const targets=await (await fetch('/assets/downloads/capture-targets.json',{cache:'no-store'})).json();
  const folders=[...new Set(targets.map(x=>x.collection))];const inventories={};
  for (const folder of folders) inventories[folder]=await (await fetch('/library-files/'+folder+'/sources.json',{cache:'no-store'})).json();
  let checks={};try{const response=await fetch('/library-files/browser-capture-status.json',{cache:'no-store'});if(response.ok)checks=await response.json();}catch(_){}
  let reviews={};try{const response=await fetch('/api/health',{cache:'no-store'});if(!response.ok)throw new Error('Health unavailable');{const health=await response.json();if(!health.source_checks?.available)throw new Error('Schedules unavailable');reviews=Object.fromEntries((health.source_checks?.browser_review?.reviews||[]).map(r=>[r.id,r]));}}catch(_){throw new Error('Browser review schedules unavailable; try again shortly.');}
  const root=document.querySelector('#items');root.replaceChildren();
  const pending=document.createElement('div'),installed=document.createElement('details'),optional=document.createElement('details'),groups=new Map();
  const optionalSummary=document.createElement('summary');optional.append(optionalSummary);let optionalCount=0;
  const summary=document.createElement('summary');installed.append(summary);let installedCount=0,pendingCount=0;
  for (const item of targets) {
   const record=inventories[item.collection].find(x=>x.id===item.id);
   const present=record?.status==='installed';let check=checks[item.id];const review=reviews[item.id];
   if(review){check={...check,...review,installed_sha256:record.sha256,state:review.changed?'changed':check?.state||'blocked',message:review.changed?'Publisher PDF changed; review a browser copy before replacing the saved edition.':review.review_due?'Browser review is due. The verified offline copy remains available.':'Verified offline copy retained; next browser review is scheduled below.'};}
   const category=captureCategory(item,record,check);const isOptional=category==='Optional references';const actionNeeded=category!=='Installed — no action needed' && !isOptional;const broken=item.source?.failure_kind==='broken_link';
   const section=document.createElement('section');const h=document.createElement('h2');h.textContent=item.title;section.append(h);
   const explanation=document.createElement('p');
   explanation.textContent=present?(check?.installed_sha256===record.sha256?check.message||'Verified offline copy retained.':'Installed; no current publisher comparison recorded.'):'Not installed.';
   if(check?.checked_at && present)explanation.textContent+=' Last checked '+new Date(check.checked_at).toLocaleString()+'.';section.append(explanation);
   if(review){const schedule=document.createElement('p');schedule.textContent=(review.review_due?'Browser review due':'Browser review scheduled')+' · Last verified: '+(review.last_verified?new Date(review.last_verified).toLocaleDateString():'—')+' · Next review: '+(review.next_due?new Date(review.next_due).toLocaleDateString():'Now')+' · Every '+review.review_interval_days+' days.';section.append(schedule);}
   if(!broken){const button=document.createElement('button');button.dataset.captureId=item.id;
   button.textContent=present?(check?.state==='changed'?'Capture reviewed replacement':'Compare browser copy'):'Download & import';
   if(present)button.dataset.expectedHash=record.sha256;section.append(button);
   const link=document.createElement('a');link.href=item.url;link.target='_blank';link.rel='noopener';link.dataset.armId=item.id;if(present)link.dataset.expectedHash=record.sha256;link.textContent='Open publisher download';section.append(link);}
   if(item.source?.note && (actionNeeded||isOptional)){const note=document.createElement('p');note.textContent=item.source.note;section.append(note);}
   for(const [label,url] of [['Publication page',item.source?.publication_page],['Original recorded URL',broken?item.url:null],['Review replacement candidate',item.source?.candidate?.url]]){if(url){const a=document.createElement('a');a.href=url;a.target='_blank';a.rel='noopener';a.textContent=label+' ↗';const p=document.createElement('p');p.append(a);section.append(p);}}
   if(item.source?.candidate){const p=document.createElement('p');p.textContent=item.source.candidate.title+'. '+item.source.candidate.note;section.append(p);}
   if(present){const local=document.createElement('a');local.href='/library-files/'+item.collection+'/'+record.filename;local.textContent=' · Read installed copy';section.append(local);}
   const status=document.createElement('p');status.setAttribute('role','status');section.append(status);
   if(isOptional){optional.append(section);optionalCount++;}else if(actionNeeded){if(!groups.has(category)){const group=document.createElement('div'),title=document.createElement('h2');title.textContent=category;group.append(title);groups.set(category,group);pending.append(group);}groups.get(category).append(section);pendingCount++;}else installed.append(section);
   if(!actionNeeded && !isOptional)installedCount++;
  }
  summary.textContent='Installed captures ('+installedCount+') — optional browser comparisons';
  const heading=document.createElement('h2');heading.textContent='Needs capture or review ('+pendingCount+')';root.append(heading);
  if(!pendingCount){const p=document.createElement('p');p.textContent='No capture or update review is pending.';pending.append(p);}
  optionalSummary.textContent='Optional references ('+optionalCount+') — not required';
  root.append(pending,installed);if(optionalCount)root.append(optional);
 } catch(e){document.querySelector('#error').textContent='Could not read the current Ark inventory: '+e.message;}
 finally{refreshing=false;if(refreshAgain){refreshAgain=false;loadCapture();}}
}
document.addEventListener('ark-capture-refresh',loadCapture);
loadCapture();
function updateCaptureConnection(){
 const box=document.querySelector('#connection');
 const connected=document.documentElement.dataset.arkCapture==='ready';
 box.dataset.state=connected?'connected':'disconnected';
 const heading=document.createElement('strong');
 heading.textContent=connected?'✓ Capture extension connected':'⚠ Extension not connected';
 box.replaceChildren(heading);
 if(!connected){
  const explanation=document.createElement('p');
  explanation.textContent='The installer registers the helper; it does not load the Chrome extension. In Chrome, open chrome://extensions, turn on Developer mode, choose Load unpacked, and select the extracted capture folder. If already loaded, enable or reload the extension, then reload this page in that same browser.';
  const link=document.createElement('a');link.href='/docs/20-Administration/BrowserCapture.html';link.textContent='Set up the capture extension →';
  box.append(explanation,link);
 }
 const setup=document.querySelector('#setup');
 if(setup && setup.dataset.connected!==String(connected)){
  setup.open=!connected;setup.dataset.connected=String(connected);
 }
}
setTimeout(updateCaptureConnection,1000);
new MutationObserver(updateCaptureConnection).observe(document.documentElement,{attributes:true,attributeFilter:['data-ark-capture']});


// Older installed extensions supply plain status text; recognize their failure
// messages too, so error presentation does not require reinstalling the extension.
function styleCaptureErrors(){
 for(const output of document.querySelectorAll('#items section > [role="status"],#update-status,#error')){
  const text=output.textContent.trim();
  const failed=!!text && (output.id==='error'||/not accepted|not supported|failed|\berror\b|unavailable|interrupted|could not|refused|did not match|not enough|no file was installed|use the ark capture page/i.test(text));
  output.classList.toggle('capture-error',failed);
  output.classList.toggle('capture-progress',!failed && /^(Downloaded;|Downloading|Checking installed|Retrying \d)|validating and importing/i.test(text));
  const live=failed?'assertive':'polite';
  if(output.getAttribute('aria-live')!==live)output.setAttribute('aria-live',live);
 }
}
new MutationObserver(styleCaptureErrors).observe(document.querySelector('main'),{childList:true,subtree:true,characterData:true});
styleCaptureErrors();
