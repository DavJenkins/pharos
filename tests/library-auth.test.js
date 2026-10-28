const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
function harness(){
  const nodes=new Map(), requests=[], hooks={};
  let now=1000, status=200, remember=false, saved=false, prompts=0;
  const auth={isRemembered:()=>saved,forget:()=>{saved=false;},rejected:r=>{if(r.status===401)saved=false;},authorization:async()=>{if(!saved)prompts++;saved=remember;return "Basic test-authorization";}};
  const element=id=>{if(!nodes.has(id))nodes.set(id,{value:'',hidden:false,required:true,disabled:false,textContent:'',replaceChildren(){},append(){},addEventListener(){},showModal(){},close(){}});return nodes.get(id);};
  const context=vm.createContext({document:{getElementById:element,createElement:()=>element(Symbol())},window:{CaretakerAuth:auth,addEventListener:(n,f)=>hooks[n]=f},TextEncoder,btoa:s=>Buffer.from(s,'binary').toString('base64'),Date:{now:()=>now},setInterval(){},fetch:async(url,options={})=>{
    requests.push({url,options});
    const inventory={downloads_enabled:true,storage_ready:true,free_bytes:100,installed:[],pending:[],removed:[],progress:{label:'Idle'}};
    return {ok:!url.endsWith('/install')&&!url.endsWith('/unlock')||status===200,status,json:async()=>url.endsWith('/install')?{message:'Requested',detail:'Wrong password'}:inventory};
  }});
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../app/static/assets/js/library.js'),'utf8'),context);
  const choose=()=>vm.runInContext('choose({id:"example",title:"Example",repository_id:"example",release:"example.zim",bytes:100},"install")',context);
  const submit=()=>element('download-form').onsubmit({preventDefault(){}});
  return {element,requests,choose,submit,hooks,remember:()=>{remember=true;},prompts:()=>prompts,follow:data=>{context.progressData=data;vm.runInContext("followDownload(progressData)",context);},setStatus:n=>status=n,expire:()=>{now+=16*60*1000;saved=false;vm.runInContext('authUI()',context);}};
}
test('password prompt is on demand, not embedded in the library confirmation',async()=>{
 const h=harness();h.choose();assert.equal(h.prompts(),0);assert.equal(h.element('password-row').hidden,true);assert.equal(h.element('password').required,false);await h.submit();h.choose();await h.submit();assert.equal(h.prompts(),2);
});
test('opt-in shared authentication is reused until expiry',async()=>{
 const h=harness();h.remember();h.choose();await h.submit();h.choose();await h.submit();assert.equal(h.prompts(),1);h.expire();h.choose();await h.submit();assert.equal(h.prompts(),2);
});
test('authentication rejection clears remembered authentication',async()=>{
 const h=harness();h.remember();h.choose();await h.submit();h.choose();h.setStatus(401);await h.submit();assert.equal(h.element('lock-library').hidden,true);
});
test('explicit lock clears shared authentication',async()=>{
 const h=harness();h.remember();h.choose();await h.submit();h.element('lock-library').onclick();assert.equal(h.element('lock-library').hidden,true);
});

test('queued, active, and completed downloads have distinct states',async()=>{
 const h=harness();h.choose();h.element('password').value='test';await h.submit();assert.equal(h.element('operation-heading').textContent,'Download queued');
 h.follow({installed:[],progress:{state:'downloading',label:'Downloading 25%'}});assert.equal(h.element('operation-heading').textContent,'Download in progress');
 h.follow({installed:[{id:'example'}],progress:{state:'activating',label:'Activating'}});assert.equal(h.element('operation-heading').textContent,'Activating collection');
 h.follow({installed:[{id:'example'}],progress:{state:'idle',label:'Idle'}});assert.equal(h.element('operation-heading').textContent,'Download complete');assert.equal(h.element('download').hidden,true);
});
