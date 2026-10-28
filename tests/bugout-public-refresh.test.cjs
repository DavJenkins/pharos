const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
test('initial and scheduled bug-out status checks never ask for caretaker authentication',async()=>{
 const nodes=new Map(),requests=[],intervals=[];let prompts=0;
 const element=id=>{if(!nodes.has(id))nodes.set(id,{hidden:false,disabled:false,textContent:'',value:'',checked:false,addEventListener(){},replaceChildren(){},append(){},reset(){},showModal(){},close(){},reportValidity:()=>true});return nodes.get(id);};
 const context=vm.createContext({document:{hidden:false,getElementById:element,createElement:()=>element(Symbol()),createTextNode:text=>({textContent:text}),addEventListener(){}},window:{CaretakerAuth:{authorization:async()=>{prompts++;throw Error('A public status check must not authenticate');}}},fetch:async(url,options)=>{requests.push({url,options});return {ok:true,json:async()=>({configured:false,ready:false,tasks:[]})};},AbortSignal,Date,setInterval:fn=>intervals.push(fn)});
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../app/static/assets/js/bugout.js'),'utf8'),context);
 await new Promise(setImmediate);
 assert.equal(prompts,0);assert.equal(requests.length,1);assert.equal(requests[0].url,'/api/bugout/state');assert.equal(requests[0].options.headers,undefined);
 intervals[0]();await new Promise(setImmediate);
 assert.equal(prompts,0);assert.equal(requests.length,2);
});
