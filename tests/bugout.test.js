"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm"),path=require("node:path");
const source=fs.readFileSync(path.join(__dirname,"../app/static/assets/js/bugout.js"),"utf8");
function node(){return {hidden:true,disabled:false,value:"",checked:false,textContent:"",listeners:{},children:[],
 addEventListener(k,fn){this.listeners[k]=fn;},append(...v){this.children.push(...v);},replaceChildren(){this.children=[];},
 reportValidity(){return true;},reset(){},showModal(){this.open=true;},close(){this.open=false;this.listeners.close?.();}};}
async function scenario(state,failed=false,testResult={ok:true,message:"Share readable; not saved"}){
 const ids=["bugout-warning","bugout-test-credentials","bugout-sync","bugout-stop","bugout-continue","bugout-panel","bugout-start","bugout-dialog","bugout-form","bugout-readiness","bugout-operation","bugout-tasks","bugout-cancel","bugout-submit","bugout-admin","bugout-password","bugout-username","bugout-domain","bugout-remember","bugout-form-result","bugout-credential-fields","bugout-dialog-title"];
 const elements=Object.fromEntries(ids.map(k=>[k,node()]));const calls=[],timers=[];
 vm.runInNewContext(source,{window:{CaretakerAuth:{authorization:async()=>"Basic test-auth",rejected(){}}},document:{hidden:false,getElementById:k=>elements[k],createElement:node,createTextNode:s=>s,addEventListener(){}},
 setInterval:f=>timers.push(f),AbortSignal:{timeout(){}},TextEncoder,Uint8Array,crypto:require("node:crypto").webcrypto,btoa:s=>Buffer.from(s).toString("base64"),
 fetch:async(url,options)=>{calls.push([url,options]);if(failed)throw Error("offline");return {ok:true,json:async()=>url.endsWith("/test") ? testResult : state};}});
 await new Promise(resolve=>setImmediate(resolve));
 return {elements,calls,timers};
}
(async()=>{
 let s=await scenario({configured:false,ready:false,reason:"No tasks",tasks:[]});
 assert.equal(s.elements["bugout-panel"].hidden,true);assert.equal(s.elements["bugout-start"].disabled,true);
 for (const operation of [null,{id:"done",state:"completed"},{id:"failed",state:"failed"},{id:"cancelled",state:"cancelled"},{id:"prefetch",mode:"prefetch",state:"running"}]) {
   s=await scenario({configured:true,ready:true,tasks:[],operation});
   for (const id of ["bugout-stop","bugout-continue"]) {
     assert.equal(s.elements[id].hidden,true);assert.equal(s.elements[id].disabled,true);
     s.elements[id].listeners.click();assert.notEqual(s.elements["bugout-dialog"].open,true);
   }
 }
 s=await scenario({configured:true,ready:false,reason:"No source",tasks:[{id:"one",title:"Private documents",ready:false,reason:"Credentials required",credential_configured:true}]});
 assert.equal(s.elements["bugout-panel"].hidden,false);assert.equal(s.elements["bugout-start"].disabled,true);
 assert.equal(s.elements["bugout-readiness"].textContent,"No source");
 s.elements["bugout-start"].listeners.click();assert.notEqual(s.elements["bugout-dialog"].open,true);
 s=await scenario({configured:true,ready:true,tasks:[{id:"one",title:"Documents",ready:true,reason:"Ready"}]});
 assert.equal(s.elements["bugout-start"].disabled,false);s.elements["bugout-start"].listeners.click();
 assert.equal(s.elements["bugout-dialog"].open,true);
 s.elements["bugout-admin"].value="secret";
 await s.elements["bugout-form"].listeners.submit({preventDefault(){}});
 const call=s.calls.find(([url])=>url.endsWith("/trigger"));assert.ok(call);
 assert.match(JSON.parse(call[1].body).operation_id,/^[0-9a-f-]{36}$/);
 assert.equal(s.elements["bugout-admin"].value,"");
 s=await scenario({configured:true,ready:false,reason:"Bugout already running",tasks:[],operation:{state:"running",updated:new Date().toISOString()}});
 assert.equal(s.elements["bugout-start"].disabled,true);
 s=await scenario({configured:true,ready:false,sync_ready:true,bugout_configured:false,tasks:[]});
 assert.equal(s.elements["bugout-start"].hidden,true);
 assert.equal(s.elements["bugout-sync"].disabled,false);
 s.elements["bugout-sync"].listeners.click();
 await s.elements["bugout-form"].listeners.submit({preventDefault(){}});
 assert.ok(s.calls.some(([url])=>url.endsWith("/sync")));
 s=await scenario({configured:true,ready:false,tasks:[],operation:{id:"running-operation",state:"running",updated:new Date().toISOString()}});
 assert.equal(s.elements["bugout-continue"].hidden,false);
 s.elements["bugout-continue"].listeners.click();
 await s.elements["bugout-form"].listeners.submit({preventDefault(){}});
 const cancel=s.calls.find(([url])=>url.endsWith("/cancel"));
 assert.deepEqual(JSON.parse(cancel[1].body),{operation_id:"running-operation",continue_updates:true});
 for (const result of [{ok:true,message:"Share readable; not saved"},{ok:false,message:"Credentials rejected"}]) {
   s=await scenario({configured:true,ready:false,tasks:[{id:"manuals",title:"Manuals",ready:false,reason:"Credentials required",credential_configured:true}]},false,result);
   const row=s.elements["bugout-tasks"].children[0];
   const actions=row.children.find(n=>n?.className==="household-task-actions");
   assert.ok(actions,"Credential actions share the dedicated button row");
   actions.children.find(n=>n?.textContent==="Set credentials").listeners.click();
   s.elements["bugout-admin"].value="admin-secret";
   s.elements["bugout-username"].value="dave";
   s.elements["bugout-password"].value="share-secret";
   s.elements["bugout-domain"].value="WORKGROUP";
   await s.elements["bugout-test-credentials"].listeners.click();
   const testCall=s.calls.find(([url])=>url.endsWith("/manuals/test"));assert.ok(testCall);
   assert.equal(JSON.parse(testCall[1].body).password,"share-secret");
   assert.equal(s.elements["bugout-dialog"].open,true);
   assert.equal(s.elements["bugout-password"].value,"share-secret");
   assert.ok(s.elements["bugout-form-result"].textContent.includes(result.message));
   assert.equal(s.calls.filter(([,options])=>options.method==="POST").length,1);
   assert.equal(s.elements["bugout-submit"].disabled,false);
 }
 for (const [ready, checked, expected] of [[true,"2026-09-27T15:08:00Z","Source available at last check"],[false,"2026-09-27T15:08:00Z","Source unavailable at last check"],[false,null,"Source availability not checked"]]) {
   s=await scenario({configured:true,ready,tasks:[{id:"manuals",title:"Manuals",ready,checked,reason:"Status"}]});
   const notice=s.elements["bugout-tasks"].children[0].children.find(n=>n?.className==="manifest-upstream");
   assert.ok(notice.textContent.startsWith(expected));
   assert.ok(!notice.textContent.includes("2026-09-27T"));
   if (checked) assert.ok(notice.textContent.includes("checked "));
 }
 s=await scenario({configured:true,ready:true,tasks:[{id:"manuals",title:"Manuals",ready:true,reason:"Ready",credential_configured:true,credentials_saved:true,cache:{state:"failed",message:"Copy failed",checked:"2026-09-27T12:00:00Z"}}]});
 let row=s.elements["bugout-tasks"].children[0];
 assert.ok(row.children.find(n=>n?.className==="household-task-actions").children.find(n=>n?.textContent==="Update credentials"));
 assert.ok(row.children.find(n=>n?.className==="household-copy-status").textContent.includes("No completed"));
 s=await scenario({configured:true,ready:true,tasks:[{id:"manuals",title:"Manuals",ready:true,reason:"Ready",cache:{state:"completed",file:"manuals.tar",last_success:"2026-09-27T12:00:00Z"}}]});
 row=s.elements["bugout-tasks"].children[0];
 assert.equal(row.children.find(n=>n?.className==="household-copy-status").textContent,"Saved backup available on the Ark");
 const mutable={configured:true,ready:true,tasks:[{id:"manuals",title:"Manuals",ready:true,reason:"Ready",cache:{state:"failed",message:"Access denied",failure_count:4,next_attempt:"2026-10-13T08:00:00Z",file:"last-good.tar"}}]};
 s=await scenario(mutable);
 assert.equal(s.elements["bugout-warning"].hidden,false);
 assert.match(s.elements["bugout-warning"].textContent,/Manuals/);
 const problem=s.elements["bugout-tasks"].children[0].children.find(n=>n?.className==="household-warning");
 assert.match(problem.textContent,/4 consecutive/);
 assert.match(problem.textContent,/Previous successful copy/);
 assert.match(problem.textContent,/Next automatic attempt/);
 await s.timers[0]();await new Promise(resolve=>setImmediate(resolve));
 assert.equal(s.elements["bugout-warning"].hidden,false);
 mutable.tasks[0].cache={state:"completed",file:"new.tar"};
 await s.timers[0]();await new Promise(resolve=>setImmediate(resolve));
 assert.equal(s.elements["bugout-warning"].hidden,true);
 s=await scenario({},true);assert.equal(s.elements["bugout-start"].disabled,true);
 console.log("Bugout UI checks passed: hidden, unavailable, ready, authenticated trigger, active job, and API failure.");
})().catch(error=>{console.error(error);process.exitCode=1;});
