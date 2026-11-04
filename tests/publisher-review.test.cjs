const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
function harness(){
 const nodes=new Map();
 function node(){return {hidden:false,textContent:'',children:[],className:'',after(){},setAttribute(){},replaceChildren(){this.children=[];},append(...items){this.children.push(...items);},querySelector(){return this;}};}
 const dialog=node();dialog.open=true;dialog.addEventListener=()=>{};dialog.showModal=()=>{dialog.open=true;};
 dialog.querySelector=s=>{if(!nodes.has(s))nodes.set(s,node());return nodes.get(s);};
 dialog.querySelectorAll=()=>[];
 const context=vm.createContext({document:{createElement:tag=>tag==='dialog'?dialog:node(),body:{append(){}}},setInterval(){},refresh(){},window:{CaretakerAuth:{authorization:async()=> 'test'}},request:async()=>({state:'ready',job:'a',message:'Candidate verified. Choose Install.'})});
 vm.runInContext(fs.readFileSync('app/static/assets/js/publisher-review.js','utf8'),context);
 return {context,nodes,dialog,run:code=>vm.runInContext(code,context)};
}
test('ready is a confirmation state; only installed or kept is success',()=>{
 const h=harness();h.run("renderPublisherReview({state:'ready'})");
 assert.match(h.nodes.get('[data-review-status]').className,/state-confirm/);
 h.run("renderPublisherReview({state:'installed'})");
 assert.match(h.nodes.get('[data-review-status]').className,/state-success/);
});
test('a rejected action remains visible after successful progress polling',async()=>{
 const h=harness();await h.run("openPublisherReview({id:'map',title:'Map'})");
 h.context.request=async(path,options)=>{if(options)throw new Error('Source changed. Prepare again.');return {state:'ready',job:'a',message:'Candidate verified. Choose Install.'};};
 await h.run("decidePublisherReview('install')");
 await h.run('pollPublisherReview()');
 const error=h.nodes.get('[data-review-error]');assert.equal(error.hidden,false);assert.match(error.textContent,/Action not accepted: Source changed/);
 assert.match(h.nodes.get('[data-review-status]').className,/state-confirm/);
});
test('a read-only polling outage clears after recovery',async()=>{
 const h=harness();await h.run("openPublisherReview({id:'map',title:'Map'})");
 h.context.request=async()=>{throw new Error('Server unavailable');};await h.run('pollPublisherReview()');
 assert.equal(h.nodes.get('[data-review-error]').hidden,false);
 h.context.request=async()=>({state:'ready',job:'a'});await h.run('pollPublisherReview()');
 assert.equal(h.nodes.get('[data-review-error]').hidden,true);
});
test('elapsed advances without worker telemetry and installation has its own clock',()=>{
 const h=harness();
 assert.equal(h.run("publisherReviewElapsed({state:'preparing',started_at:100,telemetry:{elapsed_seconds:2}},160)"),60);
 assert.equal(h.run("publisherReviewElapsed({state:'preparing',started_at:100,telemetry:{elapsed_seconds:2}},165)"),65);
 assert.equal(h.run("publisherReviewElapsed({state:'installing',started_at:100,updated_at:150},165)"),15);
 assert.equal(h.run("publisherReviewElapsed({state:'installing',started_at:100,updated_at:160,operation_started_at:150},165)"),15);
});
