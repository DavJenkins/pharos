import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';

// Minimal DOM fixture exercises the actual vendored lexer and DOM-only renderer.
class Node {
 constructor(tag='',value=''){this.tag=tag;this.value=value;this.children=[];this.attributes={};this.style={};}
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
console.log('Banner Markdown: formatting, lists, links, tables, code, line breaks and unsafe content handling passed.');
