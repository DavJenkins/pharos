const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
function harness(){
  const nodes=new Map(), requests=[], hooks={};
  let now=1000, status=200;
  const element=id=>{if(!nodes.has(id))nodes.set(id,{value:'',hidden:false,required:true,disabled:false,textContent:'',replaceChildren(){},append(){},addEventListener(){},showModal(){},close(){}});return nodes.get(id);};
  const context=vm.createContext({document:{getElementById:element,createElement:()=>element(Symbol())},window:{addEventListener:(n,f)=>hooks[n]=f},TextEncoder,btoa:s=>Buffer.from(s,'binary').toString('base64'),Date:{now:()=>now},setInterval(){},fetch:async(url,options={})=>{
    requests.push({url,options});
    const inventory={downloads_enabled:true,storage_ready:true,free_bytes:100,installed:[],pending:[],removed:[],progress:{label:'Idle'}};
    return {ok:!url.endsWith('/install')||status===200,status,json:async()=>url.endsWith('/install')?{message:'Requested',detail:'Wrong password'}:inventory};
  }});
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../app/static/assets/js/library.js'),'utf8'),context);
  const choose=()=>vm.runInContext('choose({title:"Example",repository_id:"example",release:"example.zim",bytes:100},"install")',context);
  const submit=()=>element('download-form').onsubmit({preventDefault(){}});
  return {element,requests,choose,submit,hooks,setStatus:n=>status=n,expire:()=>{now+=16*60*1000;vm.runInContext('authUI()',context);}};
}
test('successful authentication is reused for another confirmed action',async()=>{
 const h=harness();h.choose();h.element('password').value='test-only-password';await h.submit();
 h.choose();assert.equal(h.element('password').required,false);assert.equal(h.element('password-row').hidden,true);
 await h.submit();const r=h.requests.filter(r=>r.url.endsWith('/install'));assert.equal(r.length,2);assert.equal(r[0].options.headers.Authorization,r[1].options.headers.Authorization);assert.equal(h.element('password').value,'');
});
test('expired authentication prompts again',async()=>{
 const h=harness();h.choose();h.element('password').value='test';await h.submit();h.expire();assert.equal(h.element('password').required,true);assert.equal(h.element('password-row').hidden,false);
});
test('authentication rejection clears the cached credential',async()=>{
 const h=harness();h.choose();h.element('password').value='test';await h.submit();h.choose();h.setStatus(401);await h.submit();assert.equal(h.element('password').required,true);assert.equal(h.element('lock-library').hidden,true);
});
test('explicit lock and navigation clear authentication',async()=>{
 const h=harness();h.choose();h.element('password').value='test';await h.submit();h.element('lock-library').onclick();assert.equal(h.element('password').required,true);
 h.element('password').value='test';await h.submit();h.hooks.pagehide();assert.equal(h.element('password').required,true);
});
