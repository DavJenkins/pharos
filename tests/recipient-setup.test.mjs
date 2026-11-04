import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync(new URL('../app/static/assets/js/recipient-setup.js',import.meta.url),'utf8');
async function load(state,ok=true){
 const calls=[],form={hidden:false,resets:0,reset(){this.resets++;},addEventListener(){},querySelector(){return {disabled:false};},querySelectorAll(){return [];}},result={textContent:''},hint={textContent:''};
 vm.runInNewContext(source,{document:{querySelector:()=>null,getElementById:id=>id==='setup'?form:id==='result'?result:hint},fetch:async(url,options)=>{calls.push({url,options});return {ok,json:async()=>state};}});
 assert.equal(form.hidden,true,'Hide the form while checking persisted status');
 await new Promise(resolve=>setImmediate(resolve));return {form,result,calls};
}
test('refreshing an enrolled Ark shows Ready without offering password setup',async()=>{
 for(let refresh=0;refresh<2;refresh++){
  const page=await load({setup_required:false});assert.equal(page.form.hidden,true);assert.match(page.result.innerHTML,/Setup complete\./);assert.equal(page.calls.length,1);assert.equal(page.calls[0].url,'/api/recipient/status');assert.equal(page.calls[0].options.method,undefined);
 }
});
test('pending enrollment displays the form after checking status',async()=>{const p=await load({setup_required:true,network_mode:'hotspot',hotspot_ssid:'DataArk'});assert.equal(p.form.hidden,false);});
test('failed status cannot masquerade as a new enrollment',async()=>{const p=await load({},false);assert.equal(p.form.hidden,true);assert.match(p.result.textContent,/Unable to check setup status/);});
test('eye controls hide repeat fields and keep password roles independent',async()=>{
 const fields=Object.fromEntries(['password','repeat','admin_password','admin_repeat'].map(name=>[name,{type:'password',disabled:false,value:'confirmation',label:{hidden:false},closest(){return this.label;}}]));
 const toggles=['password repeat','admin_password admin_repeat'].map(pair=>({dataset:{passwordPair:pair,passwordLabel:pair.startsWith('admin')?'Linux admin password':'caretaker password'},attrs:{},setAttribute(k,v){this.attrs[k]=v;},addEventListener(event,fn){this.click=fn;}}));
 const form={hidden:false,reset(){},addEventListener(){},elements:{namedItem:name=>fields[name]},querySelectorAll(){return toggles;}};
 vm.runInNewContext(source,{document:{querySelector:()=>null,getElementById:id=>id==='setup'?form:{}},fetch:async()=>({ok:true,json:async()=>({setup_required:true})})});
 toggles[0].click();assert.equal(fields.password.type,'text');assert.equal(fields.repeat.disabled,true);assert.equal(fields.repeat.label.hidden,true);assert.equal(toggles[0].attrs['aria-pressed'],'true');assert.equal(fields.admin_password.type,'password');
 toggles[1].click();assert.equal(fields.admin_password.type,'text');assert.equal(fields.admin_repeat.disabled,true);
 toggles[0].click();assert.equal(fields.password.type,'password');assert.equal(fields.repeat.disabled,false);assert.equal(fields.repeat.label.hidden,false);assert.equal(fields.repeat.value,'');assert.equal(fields.admin_password.type,'text');
});
