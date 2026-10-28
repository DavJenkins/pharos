const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
function harness(){
 const nodes=new Map(),requests=[];let prompts=0,enabled=true,cancel=false;
 const node=id=>{if(!nodes.has(id))nodes.set(id,{value:'',textContent:'',hidden:false,disabled:false,checked:false,children:[],selectionEnd:0,replaceChildren(){this.children=[];},append(child){this.children.push(child);},focus(){},setSelectionRange(){},click(){}});return nodes.get(id);};
 const text=()=>`system:\n  version: '1.4'\ncommunity:\n  enabled: ${enabled}\n`;
 const window={addEventListener(){},CaretakerAuth:{authorization:async()=>{prompts++;if(cancel){const error=Error('cancelled');error.name='AbortError';throw error;}return 'Basic test';},rejected(){}}};
 const context=vm.createContext({window,document:{getElementById:node,querySelectorAll:()=>[],createElement:()=>node(Symbol())},fetch:async(url,options={})=>{requests.push({url,options});if(url.endsWith('/community')){enabled=JSON.parse(options.body).enabled;return {ok:true,json:async()=>({id:'job',state:'queued'})};}if(url.endsWith('/status'))return {ok:true,json:async()=>({id:'job',state:'ready',message:'Published'})};if(url.endsWith('/validate'))return {ok:true,json:async()=>({cards:[],assets:0,categories:0,community_enabled:enabled})};return {ok:true,json:async()=>({revision:'revision',text:text(),community_enabled:enabled,history:[],status:{state:'ready'}})};},Date,AbortSignal,confirm:()=>true,setTimeout,URL:{},Blob});
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../app/static/assets/js/configuration.js'),'utf8'),context);
 return {node,requests,prompts:()=>prompts,cancel:()=>cancel=true,settle:()=>new Promise(setImmediate)};
}
test('configuration page does not prompt until Load is requested',async()=>{
 const h=harness();assert.equal(h.prompts(),0);assert.equal(h.requests.length,0);h.node('configuration-load').onclick();await h.settle();assert.equal(h.prompts(),1);assert.equal(h.node('configuration-controls').hidden,false);assert.equal(h.node('community-enabled').checked,true);
});
test('Community toggle publishes the boolean and refreshes using the same authorization',async()=>{
 const h=harness();h.node('configuration-load').onclick();await h.settle();h.node('community-enabled').checked=false;h.node('community-enabled').onchange();await h.settle();
 const change=h.requests.find(item=>item.url.endsWith('/community'));assert.deepEqual(JSON.parse(change.options.body),{enabled:false,revision:'revision'});assert.equal(h.node('community-enabled').checked,false);assert.equal(h.prompts(),2);
});
test('unsaved YAML prevents a Community toggle from silently discarding edits',async()=>{
 const h=harness();h.node('configuration-load').onclick();await h.settle();h.node('configuration-text').value+='changed: true\n';h.node('configuration-text').oninput();h.node('community-enabled').checked=false;h.node('community-enabled').onchange();await h.settle();assert.equal(h.node('community-enabled').checked,true);assert.equal(h.requests.filter(item=>item.url.endsWith('/community')).length,0);
});
test('cancelled authorization restores the saved Community switch state',async()=>{
 const h=harness();h.node('configuration-load').onclick();await h.settle();h.cancel();h.node('community-enabled').checked=false;h.node('community-enabled').onchange();await h.settle();assert.equal(h.node('community-enabled').checked,true);assert.equal(h.requests.filter(item=>item.url.endsWith('/community')).length,0);
});
test('editing after validation disables Save until the new text is validated',async()=>{
 const h=harness();h.node('configuration-load').onclick();await h.settle();await h.node('configuration-validate').onclick();assert.equal(h.node('configuration-save').disabled,false);h.node('configuration-text').value+='\n';h.node('configuration-text').oninput();assert.equal(h.node('configuration-save').disabled,true);
});
