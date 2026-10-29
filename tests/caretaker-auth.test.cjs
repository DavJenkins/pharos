const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
function harness(storage=new Map()) {
  const nodes=new Map(),timers=new Map();let now=100000,status=200,calls=0,nextTimer=1;
  const node=selector=>{if(!nodes.has(selector))nodes.set(selector,{value:'',checked:false,disabled:false,textContent:'',listeners:{},querySelector:node,querySelectorAll:()=>[node('[type="submit"]'),node('#caretaker-auth-close')],setAttribute(){},focus(){},select(){},reportValidity:()=>true,reset(){node('#caretaker-auth-remember').checked=false;node('#caretaker-auth-minutes').value='10';},addEventListener(name,fn){this.listeners[name]=fn;},showModal(){this.open=true;},close(){this.open=false;const fn=this.listeners.close;delete this.listeners.close;fn?.();}});return nodes.get(selector);};
  const listeners={};const window={addEventListener(name,fn){listeners[name]=fn;},dispatchEvent(event){listeners[event.type]?.();}};
  const context=vm.createContext({window,document:{createElement:tag=>node(tag),querySelector:()=>null,body:{append(){},prepend(){}}},sessionStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},TextEncoder,AbortController,Event:class{constructor(type){this.type=type;}},Date:{now:()=>now},btoa:s=>Buffer.from(s,'binary').toString('base64'),setTimeout:(fn,ms)=>{const id=nextTimer++;timers.set(id,{fn,at:now+ms});return id;},clearTimeout:id=>timers.delete(id),fetch:async()=>{calls++;return {ok:status===200,status};}});
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../app/static/assets/js/caretaker-auth.js'),'utf8'),context);
  return {auth:window.CaretakerAuth,node,storage,calls:()=>calls,setStatus:value=>status=value,
    advance:ms=>{now+=ms;for(const [id,item] of [...timers])if(item.at<=now){timers.delete(id);item.fn();}},
    submit:async(password='test-password',minutes=null)=>{node('#caretaker-auth-password').value=password;if(minutes!==null){node('#caretaker-auth-remember').checked=true;node('#caretaker-auth-minutes').value=String(minutes);}await node('form').onsubmit({preventDefault(){}});}};
}
test('without remember, each action requires a fresh popup and stores no credential',async()=>{
 const h=harness();let first=h.auth.password('First');await h.submit();assert.equal(await first,'test-password');assert.equal(h.auth.isRemembered(),false);assert.equal(h.storage.size,0);
 let second=h.auth.password('Second');assert.equal(h.node('dialog').open,true);await h.submit();await second;assert.equal(h.calls(),2);
});
test('chosen remember interval is reused across page instances, then expires',async()=>{
 const h=harness();const initial=h.auth.authorization();await h.submit('secret',3);const header=await initial;
 assert.equal(await h.auth.authorization(),header);assert.equal(h.calls(),1);
 const next=harness(h.storage);assert.equal(next.auth.cachedAuthorization(),header);
 h.advance(3*60000);assert.equal(h.auth.isRemembered(),false);assert.equal(h.storage.size,0);
});
test('wrong password stays in popup and never becomes remembered',async()=>{
 const h=harness();h.setStatus(401);const pending=h.auth.password();await h.submit('wrong',10);assert.equal(h.auth.isRemembered(),false);assert.equal(h.node('dialog').open,true);assert.match(h.node('#caretaker-auth-error').textContent,/not accepted/);
 h.setStatus(200);await h.submit('right',10);assert.equal(await pending,'right');
});
test('closing the popup cancels the action and clears its input',async()=>{
 const h=harness();const pending=h.auth.password();h.node('#caretaker-auth-password').value='secret';h.node('#caretaker-auth-close').onclick();await assert.rejects(pending,{name:'AbortError'});assert.equal(h.node('#caretaker-auth-password').value,'');assert.equal(h.calls(),0);
});
test('authentication rejection and explicit forget clear remembered credentials',async()=>{
 const h=harness();const pending=h.auth.password();await h.submit('secret',10);await pending;h.auth.rejected({status:401});assert.equal(h.auth.cachedAuthorization(),null);
 const again=h.auth.password();await h.submit('secret',10);await again;h.auth.forget();assert.equal(h.auth.isRemembered(),false);assert.equal(h.storage.size,0);
});
test('a page disabling all buttons cannot disable the shared popup controls',async()=>{
 const h=harness();h.node('[type="submit"]').disabled=true;h.node('#caretaker-auth-close').disabled=true;const pending=h.auth.password();assert.equal(h.node('[type="submit"]').disabled,false);assert.equal(h.node('#caretaker-auth-close').disabled,false);h.node('dialog').close();await assert.rejects(pending);
});

test('cached authorization shows remaining time without prompting and Lock now clears it',async()=>{
 const h=harness();assert.equal(h.calls(),0);const pending=h.auth.password();await h.submit('secret',3);await pending;
 assert.equal(h.node('div').hidden,false);assert.match(h.node('#caretaker-auth-remaining').textContent,/3 min remaining/);
 h.advance(61000);assert.match(h.node('#caretaker-auth-remaining').textContent,/2 min remaining/);assert.equal(h.calls(),1);
 h.node('#caretaker-auth-lock').onclick();assert.equal(h.node('div').hidden,true);assert.equal(h.auth.isRemembered(),false);assert.equal(h.storage.size,0);
});
test('indicator reappears on navigation and disappears on expiry or rejection',async()=>{
 const h=harness();const pending=h.auth.password();await h.submit('secret',1);await pending;
 const next=harness(h.storage);assert.equal(next.node('div').hidden,false);assert.equal(next.calls(),0);
 h.advance(60000);assert.equal(h.node('div').hidden,true);
 next.auth.rejected({status:401});assert.equal(next.node('div').hidden,true);
});

test('floating unlocked padlock is visible only while cached and locks on click',async()=>{
 const h=harness();const pending=h.auth.password();await h.submit('secret',10);await pending;
 assert.equal(h.node('button').hidden,false);assert.match(h.node('button').title,/10 min remaining/);
 h.node('button').onclick();assert.equal(h.node('button').hidden,true);assert.equal(h.auth.isRemembered(),false);
});
