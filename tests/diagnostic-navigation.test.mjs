import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const help=fs.readFileSync('app/static/assets/js/status-help.js','utf8');
const context={};vm.createContext(context);vm.runInContext(help.slice(0,help.indexOf('(() =>')),context);
test('the first annotated tab opens rather than an unrelated healthy tab',()=>{
 const content={id:'content.source_checks',message:'Check failures'};
 assert.equal(context.arkDefaultSystemTab([content]),'library');
 assert.equal(context.arkDefaultSystemTab([{id:'usage.telemetry'}]),'usage');
 assert.equal(context.arkDefaultSystemTab([{id:'https.certificate'},content]),'system');
 assert.equal(context.arkDefaultSystemTab([]),'system');
 assert.equal(context.arkSystemTabIssues([content]).system.length,0);
});
const links=fs.readFileSync('app/static/assets/js/manifest-links.js','utf8');
vm.runInContext(links.slice(links.indexOf('function arkCardIssues'),links.indexOf('(() => {',links.indexOf('function arkCardIssues'))),context);
vm.runInContext(fs.readFileSync('app/static/assets/js/content-progress.js','utf8'),context);
test('only affected cards are flagged; shared source URLs count once',()=>{
 const items=[{id:'one',update:{pending_change:true,source_url:'shared'}},{id:'two',update:{pending_change:true,source_url:'shared'}},{id:'three',update:{result:'error',source_url:'failed'}},{id:'four',update:{result:'unchanged'}},{id:'five',update:{result:'browser_review_due'}}];
 const issues=context.arkCardIssues(items,['one','two','three','four','five']);
 assert.equal(issues.changes.length,1);assert.equal(issues.failures.length,1);assert.equal(issues.reviews.length,1);
 assert.equal(context.arkCardIssues(items,['four']).changes.length,0);
 assert.equal(context.arkCardIssues(items,[]).failures.length,0);
});
test('progress pies belong only to the active asset and use whole percentages',()=>{
 const progress={state:'activating',asset_id:'map',percent:42.876,phase:'Backing up installed map'};
 assert.equal(context.arkCardProgress(progress,['map']).percent,43);
 assert.equal(context.arkCardProgress(progress,['other']),null);
 assert.equal(context.arkCardProgress({...progress,state:'waiting'},['map']),null);
 assert.equal(context.arkCardProgress({...progress,percent:null},['map']),null);
 assert.equal(context.arkCardProgress({state:'downloading',asset:'Book',percent:17.4},['book'],[{id:'book',title:'Book'}]).percent,17);
});
test('compound progress keeps step count separate from step percentage',()=>{
 const progress={state:'activating',asset_id:'map',step:3,total_steps:5,percent:42.8};
 const result=context.arkCardProgress(progress,['map']);
 assert.equal(result.step,3);assert.equal(result.total,5);assert.equal(result.percent,43);
 assert.equal(context.arkCardProgress({...progress,step:5,percent:null},['map']).percent,null);
 assert.equal(context.arkCardProgress({...progress,step:6,percent:null},['map']),null);
 const segments=context.arkStepSegments(3,5);
 assert.equal((segments.match(/#d9b74e/g)||[]).length,2);
 assert.equal((segments.match(/#168fd0/g)||[]).length,1);
 assert.equal((segments.match(/#c8d2da/g)||[]).length,2);
});
test('both pages load the shared progress component before its consumers',()=>{
 for(const [file,consumer] of [['app/templates/index.html','assets/js/manifest-links.js'],['app/static/library.html','/assets/js/library.js']]){
  const html=fs.readFileSync(file,'utf8');
  assert.ok(html.includes('/assets/css/content-progress.css'));
  assert.ok(html.indexOf('/assets/js/content-progress.js')<html.indexOf(consumer));
 }
});
test('installed-only control is hidden when filtering cannot hide any card',()=>{
 function run(installed){
  const wrapper={},cards=installed.map(value=>({dataset:{installed:String(value)}})),section={querySelectorAll:()=>cards,append(){}};
  const toggle={closest:name=>name==='.manifest-category'?section:name==='.source-heading'?{dataset:{}}:wrapper,addEventListener(){}};
  const ctx={document:{getElementById:()=>toggle,createElement:()=>({})},localStorage:{getItem:()=>null},Array};vm.createContext(ctx);
  const start=links.indexOf('// This is a browser display preference');
  vm.runInContext(links.slice(start,links.indexOf('function arkCardIssues')),ctx);return wrapper.hidden;
 }
 assert.equal(run([true,true]),true);assert.equal(run([true,false]),false);assert.equal(run([]),true);
});
