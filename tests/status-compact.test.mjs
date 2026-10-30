import fs from 'node:fs';import vm from 'node:vm';import assert from 'node:assert/strict';
const src=fs.readFileSync('app/static/assets/js/status-compact.js','utf8');let tick;let clock=0;const events={};const classes=new Set();const gear={setAttribute(){}};const settings={open:false,querySelector:()=>gear,addEventListener:(name,fn)=>events[name]=fn};const panel={append(){},classList:{toggle:(n,on)=>on?classes.add(n):classes.delete(n)}};const online={dataset:{online:'true'}};
const data={status:{state:'ok',sync:'Idle',issues:[],health:{state:'ok',source_checks:{}}},network:{ethernet:{enabled:true},wifi:{enabled:true},access_point:{active:true}}};
const context={document:{createElement:()=>({style:{}}),querySelector:()=>panel,getElementById:id=>id==='ark-settings'?settings:online},window:{addEventListener:(n,f)=>events[n]=f},Dashboard:{refreshEnabled:true,refreshIntervalSeconds:60},DataArkStatus:{data},Date:{now:()=>clock},setInterval:f=>tick=f};vm.createContext(context);vm.runInContext(src,context);
clock=1;events['dataark:dashboard-refreshed']();clock=30000;tick();assert(!classes.has('status-condensed'));clock=30001;tick();assert(classes.has('status-condensed'));
settings.open=true;events.toggle();assert(!classes.has('status-condensed'));settings.open=false;events.toggle();clock=60001;events['dataark:dashboard-refreshed']();assert(classes.has('status-condensed'));
data.status.sync='Downloading';tick();assert(!classes.has('status-condensed'));data.status.sync='Idle';tick();clock=90001;events['dataark:dashboard-refreshed']();assert(classes.has('status-condensed'));online.dataset.online='false';events['dataark:connectivity-refreshed']();assert(!classes.has('status-condensed'));
assert(!context.arkStatusCanCondense({...data,status:{state:'error',sync:'Idle'}},true,true));assert(!context.arkStatusCanCondense(data,true,false));console.log('Compact status timing, settings, activity, connectivity and health checks passed');

assert(!context.arkStatusCanCondense({...data,status:{...data.status,health:{state:'warning'}}},true,true));
assert(!context.arkStatusCanCondense({...data,status:{...data.status,health:null}},true,true));
data.status.health.state='warning';tick();assert(!classes.has('status-condensed'));
console.log('Publisher/health warnings and missing health telemetry prevent a green compact gear');
