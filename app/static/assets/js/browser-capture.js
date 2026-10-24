async function loadCapture() {
 const root=document.querySelector('#items');
 try {
  const targets=await (await fetch('/assets/downloads/capture-targets.json',{cache:'no-store'})).json();
  const folders=[...new Set(targets.map(x=>x.collection))];const inventories={};
  for (const folder of folders) inventories[folder]=await (await fetch('/library-files/'+folder+'/sources.json',{cache:'no-store'})).json();
  for (const item of targets) {
   if(inventories[item.collection].some(x=>x.id===item.id&&x.status==='installed'))continue;
   const section=document.createElement('section');const h=document.createElement('h2');h.textContent=item.title;section.append(h);
   const button=document.createElement('button');button.dataset.captureId=item.id;button.textContent='Download & import';section.append(button);
   const link=document.createElement('a');link.href=item.url;link.target='_blank';link.rel='noopener';link.dataset.armId=item.id;link.textContent='Open publisher';section.append(link);
   const status=document.createElement('p');status.setAttribute('role','status');status.textContent='Not installed.';section.append(status);root.append(section);
  }
  if(!root.children.length)root.textContent='All supported capture targets are installed.';
 } catch(e){document.querySelector('#error').textContent='Could not read the current Ark inventory: '+e.message;}
}
loadCapture();
setTimeout(()=>{document.querySelector('#connection').textContent=document.documentElement.dataset.arkCapture==='ready'?'Capture extension connected.':'Extension not connected. Use Chrome and follow the one-time setup instructions.';},1000);
