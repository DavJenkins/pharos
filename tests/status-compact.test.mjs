import fs from 'node:fs';import vm from 'node:vm';import assert from 'node:assert/strict';
const src=fs.readFileSync('app/static/assets/js/status-compact.js','utf8');let tick,clock=0;const events={},classes=new Set();
function element(){return {style:{},dataset:{},children:[],attributes:{},append(...x){this.children.push(...x)},replaceChildren(){this.children=[]},setAttribute(k,v){this.attributes[k]=v},addEventListener(){}};}
const gear=element(),settings={open:false,before(node){panel.children.unshift(node)},querySelector:()=>gear,addEventListener:(n,f)=>events[n]=f},panel=element();panel.classList={toggle:(n,on)=>on?classes.add(n):classes.delete(n)};
const data={status:{state:'ok',sync:'Idle',issues:[],health:{state:'ok',problems:[],source_checks:{}}}};
const context={document:{createElement:element,querySelector:()=>panel,getElementById:id=>id==='ark-settings'?settings:element()},window:{addEventListener:(n,f)=>events[n]=f},Dashboard:{refreshEnabled:true,refreshIntervalSeconds:60},DataArkStatus:{data},Date:{now:()=>clock},setInterval:f=>tick=f};vm.createContext(context);vm.runInContext(src,context);
function at(t,refresh=true){clock=t;if(refresh)events['dataark:dashboard-refreshed']();else tick();}
at(1);assert.equal(gear.dataset.health,'green');at(30001);assert(classes.has('status-condensed'));
data.status.health={state:'warning',problems:[{id:'content.browser_reviews',message:'Review due'}]};at(31000);assert.equal(gear.dataset.health,'amber');assert(!classes.has('status-condensed'));assert.equal(gear.children[0].textContent,'1');
at(61000);assert(classes.has('status-condensed'));const attention=panel.children[0];assert.equal(attention.children[1].children[0].children[0].href,'/capture.html');
settings.open=true;events.toggle();assert(!classes.has('status-condensed'));assert(!attention.hidden);settings.open=false;events.toggle();at(92000);assert(classes.has('status-condensed'));
data.status.health={state:'error',problems:[{id:'service.bad',message:'Failed service'}]};at(93000);assert.equal(gear.dataset.health,'red');assert(!classes.has('status-condensed'));at(123000);assert(classes.has('status-condensed'));
data.status.sync='Downloading';data.status.update={state:'downloading'};at(124000);assert(!classes.has('status-condensed'));at(200000);assert(!classes.has('status-condensed'));
data.status.sync='Update failed';data.status.update={state:'error'};at(201000);at(231000);assert(classes.has('status-condensed'));
at(310000,false);assert.equal(gear.dataset.health,'gray');assert(!classes.has('status-condensed'));at(340000,false);assert(classes.has('status-condensed'));assert(gear.children[0].hidden);
data.status.health={state:'ok',problems:[]};data.status.sync='Idle';data.status.update={state:'idle'};at(341000);assert.equal(gear.dataset.health,'green');at(371000);assert(classes.has('status-condensed'));
assert.equal(context.arkCompactHealth(data,true,false).tone,'gray');
console.log('Passed green/amber/red/gray states, attention badge and links, new-warning expansion, stale telemetry, active work, failed idle work, and manual opening.');

