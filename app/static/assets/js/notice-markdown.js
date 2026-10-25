/* Markdown tokens become explicitly allowed DOM nodes; raw HTML is never inserted. */
(() => {
  'use strict';
  function render(target, source) {
    if (!window.marked?.lexer) { target.textContent=source; return; }
    const element=(tag, children=[])=>{const node=document.createElement(tag);node.append(...children);return node;};
    const literal=value=>document.createTextNode(value||'');
    const decode=value=>(value||'').replace(/&(?:#[0-9]+|#x[0-9a-f]+|[a-z][a-z0-9]+);/gi,reference=>{
      // Only a single entity reference reaches this inert textarea, never source markup.
      const entity=document.createElement('textarea');entity.innerHTML=reference;return entity.value;
    });
    function tokens(items) {
      const result=document.createDocumentFragment();
      for(const item of items||[])result.append(token(item));
      return result;
    }
    function token(item) {
      const inline=()=>tokens(item.tokens||[{type:'text',text:item.text||''}]);
      switch(item.type) {
        case 'space':case 'def':return literal('');
        case 'strong':return element('strong',[inline()]);
        case 'em':return element('em',[inline()]);
        case 'del':return element('del',[inline()]);
        case 'codespan':return element('code',[literal(item.text)]);
        case 'code':return element('pre',[element('code',[literal(item.text)])]);
        case 'br':return element('br');
        case 'hr':return element('hr');
        case 'heading':return element('h'+Math.max(1,Math.min(6,item.depth||1)),[inline()]);
        case 'paragraph':return element('p',[inline()]);
        case 'blockquote':return element('blockquote',[inline()]);
        case 'list': {
          const list=element(item.ordered?'ol':'ul');
          if(item.ordered && Number.isSafeInteger(item.start) && item.start>0)list.setAttribute('start',String(item.start));
          for(const entry of item.items||[]) {
            const li=element('li');
            if(entry.task) {
              const box=element('input');box.type='checkbox';box.disabled=true;box.checked=!!entry.checked;li.append(box,literal(' '));
            }
            li.append(tokens(entry.tokens));list.append(li);
          }
          return list;
        }
        case 'table': {
          const table=element('table'),head=element('tr');
          function cell(value,tag,index) {
            const node=element(tag,[tokens(value.tokens||[{type:'text',text:value.text||''}])]);
            if(['left','center','right'].includes(item.align?.[index]))node.style.textAlign=item.align[index];
            return node;
          }
          (item.header||[]).forEach((value,index)=>head.append(cell(value,'th',index)));
          table.append(element('thead',[head]));const body=element('tbody');
          for(const row of item.rows||[]) {const tr=element('tr');row.forEach((value,index)=>tr.append(cell(value,'td',index)));body.append(tr);}
          table.append(body);return table;
        }
        case 'link': {
          const label=inline();
          try {
            const url=new URL(decode(item.href),location.href);
            if(!['http:','https:','mailto:'].includes(url.protocol))return label;
            const link=element('a',[label]);link.href=url.href;
            if(item.title)link.title=item.title;
            if(url.origin!==location.origin) {link.target='_blank';link.rel='noopener noreferrer';}
            return link;
          }catch(_){return label;}
        }
        // Images stay as alt text; a banner never fetches remote images or tracking pixels.
        case 'image':return literal(decode(item.text));
        case 'html':return literal(item.text||item.raw);
        case 'text':return item.tokens?inline():literal(decode(item.text));
        case 'escape':return literal(item.text);
        default:return literal(item.raw||item.text);
      }
    }
    try {target.replaceChildren(tokens(window.marked.lexer(source,{gfm:true,breaks:true})));}
    catch(_) {target.textContent=source;}
  }
  window.ArkNoticeMarkdown=Object.freeze({render});
})();
