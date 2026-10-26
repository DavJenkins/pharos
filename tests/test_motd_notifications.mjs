import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
let value={text:'Old welcome',notification_id:'old'},busy=false;
const nodes=[],intervals=[],listeners={},storage=new Map();
class Node {
 constructor(tag){this.tag=tag;this.children=[];this.open=false;}
 append(...items){this.children.push(...items);}
 setAttribute(){}
 showModal(){this.open=true;}
 focus(){}
 querySelector(){return {focus(){}};}
}
const document={hidden:false,body:{append(node){nodes.push(node);}},createElement:tag=>new Node(tag),querySelector:()=>busy||nodes.some(n=>n.open),addEventListener:(name,fn)=>{listeners[name]=fn;}};
const context=vm.createContext({document,sessionStorage:{getItem:key=>storage.has(key)?storage.get(key):null,setItem:(key,v)=>storage.set(key,v)},fetch:async()=>({ok:true,json:async()=>value}),setInterval:fn=>intervals.push(fn),Date});
context.window=context;context.addEventListener=(name,fn)=>{listeners[name]=fn;};
context.ArkNoticeMarkdown={render:(target,text)=>{target.textContent=text;},expandVariables:text=>text,applyAppearance(){}};
vm.runInContext(fs.readFileSync(new URL('../app/static/assets/js/motd-notifications.js',import.meta.url),'utf8'),context);
await context.ArkMotdNotifications.check();assert.equal(nodes.length,0,'no old alert for new visitor');
value={text:'Updated welcome',notification_id:'new'};await context.ArkMotdNotifications.check();assert.equal(nodes.length,1);assert(nodes[0].open);
nodes[0].open=false;await context.ArkMotdNotifications.check();assert(!nodes[0].open,'no repeat after dismissal');
listeners['ark-notice-saved']({detail:{notificationId:'own'}});value={text:'Own save',notification_id:'own'};await context.ArkMotdNotifications.check();assert(!nodes[0].open,'saving client is suppressed');
busy=true;value={text:'Wait for existing dialog',notification_id:'waiting'};await context.ArkMotdNotifications.check();assert(!nodes[0].open);busy=false;intervals[1]();assert(nodes[0].open,'queued alert waits for other dialog');
nodes[0].open=false;document.hidden=true;value={text:'Background',notification_id:'hidden'};await context.ArkMotdNotifications.check();assert(!nodes[0].open);document.hidden=false;intervals[1]();assert(nodes[0].open);
nodes[0].open=false;busy=true;value={text:'Pending',notification_id:'pending'};await context.ArkMotdNotifications.check();value={text:'Unnotified newer edit',notification_id:null};await context.ArkMotdNotifications.check();busy=false;intervals[1]();assert(!nodes[0].open,'new ordinary edit supersedes queued alert');
console.log('MOTD notifications: baseline, one-time delivery, issuer suppression, dialog/visibility queue and superseding saves passed.');
