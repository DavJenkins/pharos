"use strict";
(async()=>{
 const $=id=>document.getElementById(id),bytes=n=>n>=1073741824?(n/1073741824).toFixed(2)+" GiB":(n/1048576).toFixed(1)+" MiB";
 async function refresh(){try{
  const response=await fetch('/library-files/usage.json',{cache:'no-store'});if(!response.ok)throw Error('Usage monitoring has not reported yet.');const data=await response.json();
  $('usage-status').textContent='Updated '+new Date(data.updated_at).toLocaleString()+' · Monitoring since '+new Date(data.started_at).toLocaleString()+' · Visitor counting since '+new Date(data.visitors_started_at||data.started_at).toLocaleString();
  $('usage-current').replaceChildren();
  const allTime=document.createElement('p'),allTimeNumber=document.createElement('strong');allTimeNumber.textContent=data.all_time?.estimated_visitors??'—';allTime.append(allTimeNumber,document.createTextNode('Estimated visitors · all time'));allTime.title=data.all_time?'Since '+new Date(data.all_time.started_at).toLocaleString()+'; address-based estimate':'Not recorded yet';if(data.all_time){const since=document.createElement('small');since.style.display='block';since.textContent='Since '+new Date(data.all_time.started_at).toLocaleString();allTime.append(since);}$('usage-current').append(allTime);
  const today=data.daily[new Date().toISOString().slice(0,10)];const visitor=document.createElement('p'),visitorNumber=document.createElement('strong');visitorNumber.textContent=today?.unique_visitors??'—';visitor.append(visitorNumber,document.createTextNode('Estimated visitors today (UTC)'));$('usage-current').append(visitor);
  for(const [label,key] of [['Hotspot devices','hotspot_devices'],['SSH connections','ssh_connections'],['Desktop connections','desktop_connections'],['Web terminal connections','terminal_connections']]){const p=document.createElement('p'),n=document.createElement('strong');n.textContent=data.current[key]??'—';p.append(n,document.createTextNode(label));$('usage-current').append(p);}
  const days=[];for(let i=6;i>=0;i--){const date=new Date();date.setUTCDate(date.getUTCDate()-i);const key=date.toISOString().slice(0,10);days.push([key,data.daily[key]]);}
  const max=Math.max(1,...days.map(([,v])=>v?.opens||0)),collections={};$('usage-chart').replaceChildren();$('usage-days').replaceChildren();
  for(const [day,v] of days){const column=document.createElement('div'),bar=document.createElement('span');bar.className='bar';bar.style.height=(v?Math.max(2,v.opens/max*130):2)+'px';column.title=day+': '+(v?v.opens+' requests':'No observations');column.append(document.createTextNode(v?v.opens:'—'),bar,document.createTextNode(day.slice(5)));$('usage-chart').append(column);
   const tr=document.createElement('tr');for(const text of [day,v?.unique_visitors??'—',v?.opens??'—',v?bytes(v.bytes):'—',v?.hotspot_peak??'—']){const td=document.createElement('td');td.textContent=text;tr.append(td);}$('usage-days').append(tr);
   for(const [name,count] of Object.entries(v?.collections||{}))collections[name]=(collections[name]||0)+count;
  }
  $('usage-collections').replaceChildren();for(const [name,count] of Object.entries(collections).sort((a,b)=>b[1]-a[1]).slice(0,15)){const li=document.createElement('li');li.textContent=name.replaceAll('-',' ')+' — '+count;$('usage-collections').append(li);}
  if(!Object.keys(collections).length)$('usage-collections').textContent='No document requests recorded yet.';
 }catch(error){$('usage-status').textContent=error.message;}}
 await refresh();setInterval(()=>{if(!document.hidden)refresh();},60000);
})();
