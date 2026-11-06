import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync(new URL('../app/static/assets/js/storage.js',import.meta.url),'utf8');
async function setup(mounted){
 const elements=new Map(),calls=[];let poll;
 function el(id){if(!elements.has(id))elements.set(id,{value:id==='mode'?'replace':id==='configuration'?'keep':'drive-id',checked:id==='copy-existing',hidden:false,disabled:false,textContent:'',classList:{toggle(){}},replaceChildren(){}});return elements.get(id);}
 const ctx={document:{getElementById:el,createElement:()=>({})},window:{ApplianceJobs:{async action(data){calls.push(data);return {target:'drive',copy_bytes:100,target_files_count:1};}}},fetch:async()=>({ok:true,json:async()=>({library_mounted:mounted,phase:'idle'})}),setInterval:fn=>{poll=fn;},confirm:()=>false};
 vm.runInNewContext(source,ctx);await new Promise(setImmediate);
 return {el,calls,async poll(value){mounted=value;await poll();},async preview(){await el('preview').onclick();}};
}
test('available source defaults to copying before replacement',async()=>{const s=await setup(true);assert.equal(s.el('copy-existing').checked,true);assert.equal(s.el('copy-existing').disabled,false);await s.preview();assert.equal(s.calls[0].copy_existing,true);});
test('missing source disables copying and previews replacement without copy',async()=>{const s=await setup(false);assert.equal(s.el('copy-existing').checked,false);assert.equal(s.el('copy-existing').disabled,true);await s.preview();assert.equal(s.calls[0].copy_existing,false);});
test('explicitly opting out survives status refreshes',async()=>{const s=await setup(true);s.el('copy-existing').checked=false;s.el('copy-existing').onchange();await s.poll(true);await s.preview();assert.equal(s.calls[0].copy_existing,false);});
test('adoption of a populated drive never requests copying over it',async()=>{const s=await setup(true);s.el('mode').value='adopt';s.el('mode').onchange();assert.equal(s.el('copy-label').hidden,true);await s.preview();assert.equal(s.calls[0].copy_existing,false);});
test('source disconnection invalidates an existing copy plan',async()=>{const s=await setup(true);await s.preview();await s.poll(false);assert.equal(s.el('plan').hidden,true);assert.equal(s.el('apply').hidden,true);assert.equal(s.el('copy-existing').disabled,true);});

test('unknown source status cannot silently disable copying and continue',async()=>{const s=await setup(undefined);await s.preview();assert.equal(s.calls.length,0);assert.match(s.el('message').textContent,/Wait for the current library status/);});
