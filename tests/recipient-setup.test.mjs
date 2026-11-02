import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync(new URL('../app/static/assets/js/recipient-setup.js',import.meta.url),'utf8');
async function load(state,ok=true){
 const calls=[],form={hidden:false,resets:0,reset(){this.resets++;},addEventListener(){},querySelector(){return {disabled:false};}},result={textContent:''},hint={textContent:''};
 vm.runInNewContext(source,{document:{getElementById:id=>id==='setup'?form:id==='result'?result:hint},fetch:async(url,options)=>{calls.push({url,options});return {ok,json:async()=>state};}});
 assert.equal(form.hidden,true,'Hide the form while checking persisted status');
 await new Promise(resolve=>setImmediate(resolve));return {form,result,calls};
}
test('refreshing an enrolled Ark shows Ready without offering password setup',async()=>{
 for(let refresh=0;refresh<2;refresh++){
  const page=await load({setup_required:false});assert.equal(page.form.hidden,true);assert.match(page.result.textContent,/Ready\./);assert.equal(page.calls.length,1);assert.equal(page.calls[0].url,'/api/recipient/status');assert.equal(page.calls[0].options.method,undefined);
 }
});
test('pending enrollment displays the form after checking status',async()=>{const p=await load({setup_required:true,network_mode:'hotspot',hotspot_ssid:'DataArk'});assert.equal(p.form.hidden,false);});
test('failed status cannot masquerade as a new enrollment',async()=>{const p=await load({},false);assert.equal(p.form.hidden,true);assert.match(p.result.textContent,/Unable to check setup status/);});