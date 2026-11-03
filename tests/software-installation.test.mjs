import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import fs from 'node:fs';
const source=fs.readFileSync(new URL('../app/static/assets/js/software-installation.js',import.meta.url),'utf8');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
async function page(download={state:'idle'}){
 const elements=new Map(),listeners={},calls=[],polls=[];
 const get=id=>{if(!elements.has(id))elements.set(id,{hidden:false,disabled:false,textContent:'',className:'',files:[],value:0,listeners:{},addEventListener(name,fn){this.listeners[name]=fn;},removeAttribute(name){delete this[name];}});return elements.get(id);};
 get('installation-apply').hidden=true;get('installation-download').hidden=true;
 let current=download;
 const context={document:{getElementById:get},window:{addEventListener(name,fn){listeners[name]=fn;}},CaretakerAuth:{authorization:async()=>{calls.push('authorize');return 'test';},rejected(){}},confirm:()=>true,
 setInterval(fn){polls.push(fn);return polls.length;},clearInterval(){},fetch:async(url,options)=>{
  calls.push([url,options]);
  if(url.endsWith('/download')){current={state:'verified',id:'job',tag:'software-2026.11.03',staged:{id:'verified',release:'software-2026.11.03',files:2,removals:0}};return {ok:true,json:async()=>({state:'queued'})};}
  return {ok:true,json:async()=>({configured:true,state:'idle',download:current})};
 }};
 vm.runInNewContext(source,context);await tick();await tick();
 return {get,calls,polls,release:()=>listeners['ark-release-checked']({detail:{download_available:true,channel:'stable',release:{tag:'software-2026.11.03'}}})};
}
test('online package requires explicit download and never automatically installs',async()=>{
 const p=await page();p.release();assert.equal(p.get('installation-download').hidden,false);
 assert.equal(p.calls.filter(Array.isArray).length,1);
 await p.get('installation-download').listeners.click();
 const call=p.calls.find(c=>Array.isArray(c)&&c[0].endsWith('/download'));
 assert.deepEqual(JSON.parse(call[1].body),{tag:'software-2026.11.03',preview:false});
 assert.equal(p.get('installation-apply').hidden,false);
 assert.match(p.get('installation-result').textContent,/Verified software/);
 assert.equal(p.calls.some(c=>Array.isArray(c)&&c[0].endsWith('/install')),false);
});
test('refresh restores verified package and download progress',async()=>{
 const p=await page({state:'verified',id:'job',tag:'software-2026.11.03',staged:{id:'verified',release:'software-2026.11.03',files:2,removals:0}});
 assert.equal(p.get('installation-apply').hidden,false);
 const active=await page({state:'downloading',id:'job',message:'Downloading',total_bytes:100,downloaded_bytes:42,percent:42});active.release();
 assert.equal(active.get('installation-progress').value,42);assert.equal(active.get('installation-download').disabled,true);assert.equal(active.get('installation-stage').disabled,true);
 assert.match(active.get('installation-result').textContent,/42%/);
});
test('failed download is prominent and retry remains available',async()=>{
 const p=await page({state:'failed',id:'job',message:'Signature rejected'});p.release();
 assert.match(p.get('installation-result').className,/update-error/);assert.equal(p.get('installation-apply').hidden,true);assert.equal(p.get('installation-download').disabled,false);
});
