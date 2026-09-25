"use strict";
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../app/static/assets/js/ark-connectivity.js'),'utf8');
(async()=>{
 for(const [value,ok,label] of [[true,true,'Ark online'],[false,true,'Ark offline'],[null,false,'Ark connection unknown'],['invalid',true,'Ark connection unknown']]){
  const status={};let dimmed;
  await vm.runInNewContext(source,{
   AbortController,setTimeout,clearTimeout,setInterval:()=>{},
   document:{hidden:false,addEventListener(){},getElementById:id=>id==='internet-status'?status:{classList:{toggle:(_,v)=>dimmed=v}}},
   fetch:async url=>{assert.equal(url,'/api/portal/upstream');return {ok,json:async()=>({online:value})};}
  });
  assert.equal(status.textContent,label);
  assert.equal(dimmed,label!=='Ark online');
 }
 console.log('Ark status checks passed: online, offline, API failure, and invalid response.');
})().catch(error=>{console.error(error);process.exitCode=1;});
