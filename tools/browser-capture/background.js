const HOST = 'com.dejsoftware.dataark_capture';
const activePorts = new Set();
const jobs = new Map();
function nativeRequest(payload) {
  return new Promise((resolve,reject)=>{
    const port=chrome.runtime.connectNative(HOST);activePorts.add(port);let answered=false;
    port.onMessage.addListener(result=>{answered=true;activePorts.delete(port);resolve(result);port.disconnect();});
    port.onDisconnect.addListener(()=>{activePorts.delete(port);if(!answered)reject(Error(chrome.runtime.lastError?.message||'Desktop helper disconnected.'));});
    port.postMessage(payload);
  });
}
async function setStatus(id, state, message) {
  const data = (await chrome.storage.local.get('status')).status || {};
  data[id] = {state, message}; await chrome.storage.local.set({status:data});
}
chrome.runtime.onMessage.addListener((message, sender, reply) => {
  (async () => {
    const u = new URL(sender.url);
    if (!['dataark','dataark.lan','dataark.local','192.168.40.123','192.168.40.70','192.168.8.112','192.168.4.1'].includes(u.hostname) || !['http:','https:'].includes(u.protocol) || u.pathname !== '/capture.html') throw Error('Use the Ark capture page.');
    if (message.action === 'status') return (await chrome.storage.local.get('status')).status || {};
    if (message.action === 'check_updates') {
      await setStatus('__updates__','checking','Checking installed captures against their pinned publisher URLs…');
      let result;
      try{result=await nativeRequest({operation:'check_updates'});}
      catch(e){await setStatus('__updates__','failed',e.message);throw e;}
      await setStatus('__updates__',result.ok?'checked':'failed',result.message||result.error);
      return result;
    }
    if (message.action === 'retry') {
      const d=(await chrome.storage.local.get('downloads')).downloads||{};
      for (const id of Object.keys(d)) await inspect(id);
      return {ok:true,message:Object.keys(d).length?'Retrying '+Object.keys(d).length+' captured download(s).':'No saved downloads to retry. Choose Download & import again.'};
    }
    if (message.action === 'arm') {
      const targets=await (await fetch(chrome.runtime.getURL('targets.json'))).json();
      const target=targets.find(x=>x.id===message.id); if (!target) throw Error('Unknown capture target.');
      const armed=(await chrome.storage.local.get('armed')).armed||{};
      armed[target.id]={...target,expected_sha256:message.expected_sha256,expires:Date.now()+10*60*1000}; await chrome.storage.local.set({armed});
      await setStatus(target.id,'armed','Publisher opened. Click its PDF download/save control; that download will be imported. Capture expires in ten minutes.');
      return {ok:true};
    }
    if (message.action !== 'start') throw Error('Unknown capture action.');
    const targets = await (await fetch(chrome.runtime.getURL('targets.json'))).json();
    const item = targets.find(x => x.id === message.id);
    if (!item) throw Error('This item is not an approved capture target.');
    const all = await chrome.storage.local.get('downloads');
    if (Object.values(all.downloads || {}).some(x => x.id === item.id)) throw Error('That download is already pending.');
    const downloadId = await chrome.downloads.download({url:item.url, filename:'DataArk/'+item.id+'.pdf', saveAs:false, conflictAction:'uniquify'});
    const downloads = (await chrome.storage.local.get('downloads')).downloads || {};
    downloads[downloadId] = {...item,expected_sha256:message.expected_sha256}; await chrome.storage.local.set({downloads});
    await setStatus(item.id, 'downloading', 'Downloading in Chrome…');
    await inspect(downloadId); return {ok:true};
  })().then(reply).catch(e => reply({error:e.message})); return true;
});
async function inspect(downloadId) {
  const downloads = (await chrome.storage.local.get('downloads')).downloads || {};
  const target = downloads[downloadId]; if (!target || jobs.has(downloadId)) return;
  const [item] = await chrome.downloads.search({id:Number(downloadId)}); if (!item) return;
  if (item.state === 'interrupted') {
    delete downloads[downloadId]; await chrome.storage.local.set({downloads});
    await setStatus(target.id,'failed','Chrome could not download it. Open the publisher link and check the browser.'); return;
  }
  if (item.state !== 'complete') return;
  jobs.set(downloadId,true);
  await setStatus(target.id,'importing','Downloaded; validating and importing into the Ark…');
  const port = chrome.runtime.connectNative(HOST); activePorts.add(port);
  let answered = false;
  port.onMessage.addListener(async result => {
    answered = true;
    await setStatus(target.id,result.ok?'installed':'failed',result.message || result.error || 'Import finished.');
    if(result.ok){const latest = (await chrome.storage.local.get('downloads')).downloads || {}; delete latest[downloadId]; await chrome.storage.local.set({downloads:latest});}
    jobs.delete(downloadId); activePorts.delete(port); port.disconnect();
  });
  port.onDisconnect.addListener(async () => {
    activePorts.delete(port); jobs.delete(downloadId);
    if (!answered) {
      await setStatus(target.id,'failed','Desktop helper unavailable or interrupted. Install/reconnect it, then use Retry captured files. '+(chrome.runtime.lastError?.message || ''));
    }
  });
  port.postMessage({id:target.id, filename:item.filename, url:item.url, final_url:item.finalUrl || item.url,expected_sha256:target.expected_sha256});
}
chrome.downloads.onChanged.addListener(delta => { if (delta.state) inspect(delta.id); });
chrome.downloads.onCreated.addListener(async item => {
  const armed=(await chrome.storage.local.get('armed')).armed||{};
  const clean=u=>{try {const x=new URL(u);x.hash='';return x.href;}catch(_){return '';}};
  const target=Object.values(armed).find(x=>x.expires>Date.now() && clean(x.url)===clean(item.url));
  if (!target) return;
  delete armed[target.id]; await chrome.storage.local.set({armed});
  const downloads=(await chrome.storage.local.get('downloads')).downloads||{};
  downloads[item.id]=target;await chrome.storage.local.set({downloads});await inspect(item.id);
});
// Recover completed, explicitly armed downloads after a service-worker/browser restart.
chrome.runtime.onStartup.addListener(async () => { const d=(await chrome.storage.local.get('downloads')).downloads||{}; for (const id of Object.keys(d)) inspect(id); });
