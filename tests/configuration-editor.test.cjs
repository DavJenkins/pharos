const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
function harness(modular=false){
 const nodes=new Map(),requests=[];let prompts=0,enabled=true,cancel=false;
 const node=id=>{if(!nodes.has(id))nodes.set(id,{value:'',textContent:'',hidden:false,disabled:false,checked:false,children:[],dataset:{},setAttribute(name,value){this[name]=value;},selectionEnd:0,replaceChildren(){this.children=[];},append(child){this.children.push(child);},focus(){},setSelectionRange(){},click(){}});return nodes.get(id);};
 const text=()=>`system:\n  version: '1.4'\ncommunity:\n  enabled: ${enabled}\n`;
 const window={addEventListener(){},CaretakerAuth:{authorization:async()=>{prompts++;if(cancel){const error=Error('cancelled');error.name='AbortError';throw error;}return 'Basic test';},rejected(){}}};
 const context=vm.createContext({window,document:{getElementById:node,querySelectorAll:()=>[],createElement:()=>node(Symbol())},fetch:async(url,options={})=>{requests.push({url,options});if(url.endsWith('/community')){enabled=JSON.parse(options.body).enabled;return {ok:true,json:async()=>({id:'job',state:'queued'})};}if(url.endsWith('/status'))return {ok:true,json:async()=>({id:'job',state:'ready',message:'Published'})};if(url.endsWith('/validate'))return {ok:true,json:async()=>({cards:[],assets:0,categories:0,community_enabled:enabled})};const file=modular?(new URL('http://ark'+url).searchParams.get('file')):null;return {ok:true,json:async()=>({revision:'revision',file,files:modular?[{path:'ark.yaml',read_only:false},{path:'state/order.yaml',read_only:true}]:[],read_only:file==='state/order.yaml',text:file==='state/order.yaml'?'assets: []\n':text(),community_enabled:enabled,history:[],status:{state:'ready'}})};},Date,AbortSignal,confirm:()=>true,setTimeout,URL,Blob});
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../app/static/assets/js/configuration.js'),'utf8'),context);
 return {node,requests,prompts:()=>prompts,cancel:()=>cancel=true,settle:()=>new Promise(setImmediate)};
}
test('loading public configuration requires no authorization',async()=>{
 const h=harness();assert.equal(h.prompts(),0);assert.equal(h.requests.length,0);h.node('configuration-load').onclick();await h.settle();assert.equal(h.prompts(),0);assert.equal(h.requests[0].options.headers.Authorization,undefined);assert.equal(h.node('configuration-controls').hidden,false);assert.equal(h.node('community-enabled').checked,true);
});
test('Community toggle publishes the boolean and refreshes using the same authorization',async()=>{
 const h=harness();h.node('configuration-load').onclick();await h.settle();h.node('community-enabled').checked=false;h.node('community-enabled').onchange();await h.settle();
 const change=h.requests.find(item=>item.url.endsWith('/community'));assert.deepEqual(JSON.parse(change.options.body),{enabled:false,revision:'revision'});assert.equal(h.node('community-enabled').checked,false);assert.equal(h.prompts(),1);
});
test('unsaved YAML prevents a Community toggle from silently discarding edits',async()=>{
 const h=harness();h.node('configuration-load').onclick();await h.settle();h.node('configuration-text').value+='changed: true\n';h.node('configuration-text').oninput();h.node('community-enabled').checked=false;h.node('community-enabled').onchange();await h.settle();assert.equal(h.node('community-enabled').checked,true);assert.equal(h.requests.filter(item=>item.url.endsWith('/community')).length,0);
});
test('cancelled authorization restores the saved Community switch state',async()=>{
 const h=harness();h.node('configuration-load').onclick();await h.settle();h.cancel();h.node('community-enabled').checked=false;h.node('community-enabled').onchange();await h.settle();assert.equal(h.node('community-enabled').checked,true);assert.equal(h.requests.filter(item=>item.url.endsWith('/community')).length,0);
});
test('editing after validation disables Save until the new text is validated',async()=>{
 const h=harness();h.node('configuration-load').onclick();await h.settle();await h.node('configuration-validate').onclick();assert.equal(h.prompts(),0);assert.equal(h.node('configuration-save').disabled,false);h.node('configuration-text').value+='\n';h.node('configuration-text').oninput();assert.equal(h.node('configuration-save').disabled,true);
});
test('loading a previous public version requires no authorization',async()=>{
 const h=harness();await h.node('configuration-load').onclick();h.node('configuration-history').value='previous';await h.node('configuration-restore').onclick();assert.equal(h.prompts(),0);assert.equal(h.requests.at(-1).options.headers.Authorization,undefined);
});

test('modular editor opens ark.yaml and generated state stays read-only',async()=>{
 const h=harness(true);await h.node('configuration-load').onclick();
 assert.equal(h.node('configuration-file').value,'ark.yaml');assert.equal(h.prompts(),0);
 await h.node('configuration-validate').onclick();
 assert.equal(JSON.parse(h.requests.find(r=>r.url.endsWith('/validate')).options.body).file,'ark.yaml');
 h.node('configuration-file').value='state/order.yaml';await h.node('configuration-file').onchange();
 assert.equal(h.node('configuration-text').readOnly,true);assert.equal(h.node('configuration-save').disabled,true);assert.equal(h.node('configuration-validate').disabled,true);
 h.node('configuration-file').value='ark.yaml';await h.node('configuration-file').onchange();
 assert.equal(h.node('configuration-text').readOnly,false);assert.equal(h.prompts(),0);
});

test('switching files resets section choices and single-section files are preselected',async()=>{
 const h=harness(true);await h.node('configuration-load').onclick();
 const section=h.node('configuration-section');section.value='stale';
 h.node('configuration-file').value='state/order.yaml';await h.node('configuration-file').onchange();
 assert.deepEqual(section.children.map(o=>o.textContent),['assets']);assert.equal(section.value,'0');assert.equal(section.disabled,true);
 h.node('configuration-file').value='ark.yaml';await h.node('configuration-file').onchange();
 assert.deepEqual(section.children.map(o=>o.textContent),['Choose a section…','system','community']);assert.equal(section.value,'');assert.equal(section.disabled,false);
});

test('file change clears the old editor contents synchronously before the response',async()=>{
 const h=harness(true);await h.node('configuration-load').onclick();assert.notEqual(h.node('configuration-text').value,'');
 h.node('configuration-file').value='state/order.yaml';const pending=h.node('configuration-file').onchange();
 assert.equal(h.node('configuration-text').value,'');assert.equal(h.node('configuration-section').disabled,true);assert.match(h.node('configuration-active-file').textContent,/Loading state\/order.yaml/);
 await pending;assert.equal(h.node('configuration-text').value,'assets: []\n');assert.equal(h.node('configuration-active-file').textContent,'state/order.yaml (read-only)');
});

test('unsaved indicator tracks edits and disappears after reloading saved content',async()=>{
 const h=harness(true);await h.node('configuration-load').onclick();assert.equal(h.node('configuration-unsaved').hidden,true);
 h.node('configuration-text').value+='\n';h.node('configuration-text').oninput();assert.equal(h.node('configuration-unsaved').hidden,false);
 await h.node('configuration-load').onclick();assert.equal(h.node('configuration-unsaved').hidden,true);
});
