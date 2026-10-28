import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';

// Minimal DOM fixture exercises the actual vendored lexer and DOM-only renderer.
class Node {
 constructor(tag='',value=''){this.tag=tag;this.value=value;this.children=[];this.attributes={};this.style={setProperty(key,value){this[key]=value;}};}
 append(...nodes){for(const node of nodes){if(node.tag==='#fragment')this.children.push(...node.children);else this.children.push(node);}}
 replaceChildren(...nodes){this.children=[];this.value='';this.append(...nodes);}
 setAttribute(key,value){this.attributes[key]=value;}
 get textContent(){return this.value+this.children.map(n=>n.textContent).join('');}
 set textContent(value){this.value=value;this.children=[];}
 set innerHTML(value){
   assert.equal(this.tag,'textarea');assert(/^&(?:#[0-9]+|#x[0-9a-f]+|[a-z][a-z0-9]+);$/i.test(value));
   const entities={'&amp;':'&','&lt;':'<','&gt;':'>','&quot;':'"','&colon;':':','&Tab;':'\t'};
   this.value=entities[value]||(value.startsWith('&#x')?String.fromCodePoint(parseInt(value.slice(3,-1),16)):value.startsWith('&#')?String.fromCodePoint(Number(value.slice(2,-1))):value);
 }
}
const document={createElement:tag=>new Node(tag),createTextNode:value=>new Node('#text',value),createDocumentFragment:()=>new Node('#fragment')};
const context=vm.createContext({document,URL,location:{href:'http://dataark/community.html',origin:'http://dataark'}});
vm.runInContext('window = globalThis;',context);
vm.runInContext(fs.readFileSync(new URL('../app/static/assets/vendor/marked/marked.umd.js',import.meta.url),'utf8'),context);
vm.runInContext(fs.readFileSync(new URL('../app/static/assets/js/notice-markdown.js',import.meta.url),'utf8'),context);
const render=value=>{const root=new Node('aside');context.ArkNoticeMarkdown.render(root,value);return root;};
const all=root=>[root,...root.children.flatMap(all)];
const tags=root=>all(root).map(n=>n.tag);

let root=render('# Notice\n\n**Bring water** and *a cup*, ~~no glass~~. Use `local` supplies.');
for(const tag of ['h1','strong','em','del','code'])assert(tags(root).includes(tag),tag);
assert(root.textContent.includes('Bring water'));
root=render('- First\n- Second\n\n1. One\n2. Two\n\n> Share fairly');
for(const tag of ['ul','ol','li','blockquote'])assert(tags(root).includes(tag),tag);
root=render('[Community](/community.html) and [External](https://example.org/help)');
let links=all(root).filter(n=>n.tag==='a');assert.equal(links.length,2);
assert.equal(links[0].href,'http://dataark/community.html');
assert.equal(links[1].rel,'noopener noreferrer');assert.equal(links[1].target,'_blank');
for(const value of ['[bad](javascript:alert(1))','[bad](javascript&colon;alert(1))','[bad](java&Tab;script:alert(1))','[bad](data:text/html,bad)','[bad](file:///etc/passwd)','[bad](vbscript:bad)'])assert(!tags(render(value)).includes('a'),value);
root=render('<img src=x onerror=alert(1)>\n<script>alert(1)</script>');
assert(!tags(root).some(tag=>['img','script','iframe','style','svg','form'].includes(tag)));
root=render('![Tracking pixel](https://example.org/pixel.png)');assert(!tags(root).includes('img'));assert(root.textContent.includes('Tracking pixel'));
root=render('| Time | Place |\n| --- | --- |\n| 6 PM | Ark |');assert(tags(root).includes('table'));
root=render('- [x] Ready\n- [ ] Later');let boxes=all(root).filter(n=>n.tag==='input');assert.equal(boxes.length,2);assert(boxes.every(n=>n.disabled));assert.equal(boxes[0].checked,true);
root=render('```\n<b>literal</b>\n```');assert(tags(root).includes('pre'));assert(!tags(root).includes('b'));
root=render('Line one\nLine two');assert(tags(root).includes('br'));
root=render('&lt;b&gt; &amp; &#65;');assert.equal(root.textContent,'<b> & A');assert(!tags(root).includes('b'));
root=render('`&amp;`');assert.equal(root.textContent,'&amp;');
context.ArkNoticeMarkdown.applyColor(root,'#003355');assert.equal(root.style['--ark-notice-bg'],'#003355');assert.equal(root.style['--ark-notice-fg'],'#ffffff');
context.ArkNoticeMarkdown.applyColor(root,'#ff0000');assert.equal(root.style['--ark-notice-fg'],'#000000');
context.ArkNoticeMarkdown.applyColor(root,'#fff0bd');assert.equal(root.style['--ark-notice-fg'],'#203e54');
context.ArkNoticeMarkdown.applyColor(root,'url(javascript:bad)');assert.equal(root.style['--ark-notice-bg'],'#fff0bd');
console.log('Banner Markdown: formatting, lists, links, tables, code, line breaks and unsafe content handling passed.');

const sample=new Date(2026,9,26,9,7,5);
const expand=(value,now=sample)=>context.ArkNoticeMarkdown.expandVariables(value,now);
assert.equal(expand('Good [morning]! Happy [Monday], [10/26]  Have a nice [afternoon]!'),'Good morning! Happy Monday, 10/26  Have a nice morning!');
assert.equal(expand('[date:YYYY-MM-DD] [time:HH:mm:ss] [date:ddd, MMM D]'),'2026-10-26 09:07:05 Mon, Oct 26');
assert.equal(expand('[time:h:mm A] [weekday] [unknown]'),'9:07 AM Monday [unknown]');
for(const [hour,part] of [[0,'night'],[4,'night'],[5,'morning'],[11,'morning'],[12,'afternoon'],[16,'afternoon'],[17,'evening'],[20,'evening'],[21,'night'],[23,'night']])assert.equal(expand('[daypart]',new Date(2026,9,26,hour)),part);
assert.equal(expand('[weekday] [date]',new Date(2026,9,27,0,0)),'Tuesday 10/27');
assert.equal(expand('[date:YYYY-MM-DD]',new Date(2028,1,29,12)),'2028-02-29');
root=new Node('aside');context.ArkNoticeMarkdown.render(root,'**[weekday]** [date:MM/DD] `[weekday]` [Monday](/community.html)',{variables:true,now:sample});
assert(root.textContent.includes('Monday 10/26 [weekday] Monday'));
assert.equal(all(root).find(n=>n.tag==='a').href,'http://dataark/community.html');
assert.equal(render('[weekday]').textContent,'[weekday]');
console.log('Banner variables: formatting, daypart boundaries, midnight/leap day, Markdown/code/link safety and opt-in scope passed.');

assert.equal(expand('[nextdaypart] [tomorrow] [tomorrow:YYYY-MM-DD]'),'afternoon Tuesday 2026-10-27');
for(const [hour,next] of [[1,'morning'],[9,'afternoon'],[14,'evening'],[18,'night'],[23,'morning']])assert.equal(expand('[nextdaypart]',new Date(2026,9,26,hour)),next);
assert.equal(expand('[weekpart] [nextweekpart] [thisweek] [nextweek]'),'week weekend 10/26–11/01 11/02–11/08');
assert.equal(expand('[thisweekend] [nextweekend]'),'10/31–11/01 10/31–11/01');
assert.equal(expand('[weekpart] [nextweekpart] [thisweekend] [nextweekend]',new Date(2026,9,31,12)),'weekend week 10/31–11/01 11/07–11/08');
assert.equal(expand('[thisweekend] [nextweekend]',new Date(2026,10,1,12)),'10/31–11/01 11/07–11/08');
assert.equal(expand('[tomorrow:YYYY-MM-DD]',new Date(2026,11,31,23)),'2027-01-01');
assert.equal(expand('[tomorrow:YYYY-MM-DD]',new Date(2028,1,28,23)),'2028-02-29');
assert.equal(expand('[thisweek:ddd D]'),'Mon 26–Sun 1');
console.log('Relative banner variables: daypart cycle, tomorrow, weekday/weekend boundaries, date ranges and year/leap rollover passed.');

root=new Node('aside');context.ArkNoticeMarkdown.render(root,'First **[weekday]**\nSecond `[daypart]`',{variables:true,now:sample});
const lines=all(root).filter(n=>n.attributes.class==='ark-notice-line');
assert.equal(lines.length,2);assert.equal(lines[0].textContent,'First Monday');assert.equal(lines[1].textContent,'Second [daypart]');assert(tags(root).includes('strong'));assert(tags(root).includes('code'));
console.log('Banner line groups preserve explicit breaks, formatting and literal code.');

assert.equal(expand('[today] [today:MM/DD] [TODAY:YYYY-MM-DD]'),'Monday 10/26 2026-10-26');
assert.equal(expand('[today] [today:YYYY-MM-DD]',new Date(2028,1,29,0,0)),'Tuesday 2028-02-29');
