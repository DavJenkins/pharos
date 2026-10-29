/* Markdown tokens become explicitly allowed DOM nodes; raw HTML is never inserted. */
(() => {
  'use strict';
  function dateFormat(now, format) {
    const pad=n=>String(n).padStart(2,'0'),hour=now.getHours();
    const names=(key,size)=>new Intl.DateTimeFormat('en-US',{[key]:size}).format(now);
    const values={YYYY:String(now.getFullYear()),YY:pad(now.getFullYear()%100),MMMM:names('month','long'),MMM:names('month','short'),MM:pad(now.getMonth()+1),M:String(now.getMonth()+1),DD:pad(now.getDate()),D:String(now.getDate()),dddd:names('weekday','long'),ddd:names('weekday','short'),HH:pad(hour),H:String(hour),hh:pad(hour%12||12),h:String(hour%12||12),mm:pad(now.getMinutes()),m:String(now.getMinutes()),ss:pad(now.getSeconds()),s:String(now.getSeconds()),A:hour<12?'AM':'PM',a:hour<12?'am':'pm'};
    return format.replace(/'[^']*'|YYYY|MMMM|dddd|MMM|ddd|YY|MM|DD|HH|hh|mm|ss|M|D|H|h|m|s|A|a/g,key=>key.startsWith("'")?key.slice(1,-1):values[key]);
  }
  function expandVariables(source, now=new Date()) {
    if(!Number.isFinite(now.getTime()))return source;
    const hour=now.getHours(),part=hour>=5&&hour<12?'morning':hour<17&&hour>=12?'afternoon':hour>=17&&hour<21?'evening':'night';
    return source.replace(/\[([^\[\]\n]{1,100})\]/g,(original,body)=>{
      const colon=body.indexOf(':'),key=(colon<0?body:body.slice(0,colon)).toLowerCase(),format=colon<0?null:body.slice(colon+1);
      if(['daypart','period','morning','afternoon','evening','night'].includes(key)&&format===null)return part;
      if(key==='nextdaypart'&&format===null)return {morning:'afternoon',afternoon:'evening',evening:'night',night:'morning'}[part];
      // Calendar arithmetic preserves local dates across daylight-saving transitions.
      const shift=days=>new Date(now.getFullYear(),now.getMonth(),now.getDate()+days,12);
      const weekend=[0,6].includes(now.getDay());
      if(['weekpart','currentweekpart','weekorweekend','currentweekorweekend'].includes(key)&&format===null)return weekend?'weekend':'week';
      if(['nextweekpart','upcomingweekpart','nextweekorweekend','upcomingweekorweekend'].includes(key)&&format===null)return weekend?'week':'weekend';
      if(key==='today')return dateFormat(now,format||'dddd');
      if(key==='tomorrow')return dateFormat(shift(1),format||'dddd');
      if(['thisweek','currentweek','nextweek','upcomingweek','thisweekend','currentweekend','nextweekend','upcomingweekend'].includes(key)){
        let start,end;
        const monday=-((now.getDay()+6)%7),saturday=now.getDay()===0?-1:6-now.getDay();
        if(key.endsWith('weekend')){
          const next=key.startsWith('next')||key.startsWith('upcoming');
          start=saturday+(next&&weekend?7:0);end=start+1;
        }else{
          start=monday+((key.startsWith('next')||key.startsWith('upcoming'))?7:0);end=start+6;
        }
        return dateFormat(shift(start),format||'MM/DD')+'–'+dateFormat(shift(end),format||'MM/DD');
      }
      if(['weekday','day','monday','tuesday','wednesday','thursday','friday','saturday','sunday'].includes(key))return dateFormat(now,format||'dddd');
      if(key==='date')return dateFormat(now,format||'MM/DD');
      if(key==='time')return dateFormat(now,format||'h:mm A');
      if(format===null && (/^(MM\/DD|YYYY-MM-DD)$/.test(body)||/^(0?[1-9]|1[0-2])\/(0?[1-9]|[12][0-9]|3[01])$/.test(body)))return dateFormat(now,body==='YYYY-MM-DD'?body:'MM/DD');
      return original;
    });
  }
  function highlightVariables(target, source) {
    const nodes=[];let end=0;
    for(const match of source.matchAll(/\[[^\[\]\n]*\]/g)) {
      const at=match.index,token=match[0];
      // Markdown link labels and escaped brackets are not variable references.
      if(source[at-1]==='\\'||source[at+token.length]==='('||source[at+token.length]==='[')continue;
      nodes.push(document.createTextNode(source.slice(end,at)));
      const span=document.createElement('span');
      span.setAttribute('class',expandVariables(token)!==token?'notice-variable-known':'notice-variable-unknown');
      span.textContent=token;nodes.push(span);end=at+token.length;
    }
    nodes.push(document.createTextNode(source.slice(end)+'\n'));target.replaceChildren(...nodes);
  }
  function render(target, source, options={}) {
    const now=options.now||new Date();
    const expand=value=>options.variables?expandVariables(value,now):value;
    if (!window.marked?.lexer) { target.textContent=expand(source); return; }
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
        case 'paragraph': {
          if(!options.variables)return element('p',[inline()]);
          // Balance each deliberately separated banner line independently.
          const paragraph=element('p');let line=[];
          const appendLine=()=>{const span=element('span',[tokens(line)]);span.setAttribute('class','ark-notice-line');paragraph.append(span);line=[];};
          for(const entry of item.tokens||[{type:'text',text:item.text||''}]){if(entry.type==='br')appendLine();else line.push(entry);}
          appendLine();return paragraph;
        }
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
        case 'text':return item.tokens?inline():literal(expand(decode(item.text)));
        case 'escape':return literal(item.text);
        default:return literal(item.raw||item.text);
      }
    }
    try {target.replaceChildren(tokens(window.marked.lexer(source,{gfm:true,breaks:true})));}
    catch(_) {target.textContent=source;}
  }
  function applyColor(target, value, textColor) {
    const color=/^#[0-9a-f]{6}$/i.test(value||'')?value.toLowerCase():'#fff0bd';
    const linear=channel=>{const x=channel/255;return x<=.04045?x/12.92:((x+.055)/1.055)**2.4;};
    const luminance=hex=>[.2126,.7152,.0722].reduce((sum,weight,i)=>sum+weight*linear(parseInt(hex.slice(1+i*2,3+i*2),16)),0);
    const light=luminance(color),dark=luminance('#203e54');
    const contrast=(Math.max(light,dark)+.05)/(Math.min(light,dark)+.05);
    const foreground=/^#[0-9a-f]{6}$/i.test(textColor||'')?textColor:contrast>=4.5?'#203e54':1.05/(light+.05)>=4.5?'#ffffff':'#000000';
    target.style.setProperty('--ark-notice-bg',color);
    target.style.setProperty('--ark-notice-fg',foreground);
    target.style.setProperty('--ark-notice-border',color==='#fff0bd'?'#ac852d':foreground);
  }
  function applyAppearance(target,data) {
    applyColor(target,data.color,data.text_color);
    target.setAttribute('data-banner-position',['below-header','bottom'].includes(data.position)?data.position:'top');
    target.setAttribute('data-banner-font',['old-english','serif','monospace'].includes(data.font)?data.font:'system');
    target.setAttribute('data-banner-width',['fit','margin'].includes(data.width)?data.width:'full');
    const margin=Number.isFinite(Number(data.margin))?Math.max(0,Math.min(40,Number(data.margin))):5;
    target.style.setProperty('--ark-notice-margin',margin+'%');
    for(const key of ['margin_top','margin_bottom']){const value=Number(data[key]??12);target.style.setProperty('--ark-notice-'+key.replace('_','-'),(Number.isFinite(value)?Math.max(0,Math.min(200,value)):12)+'px');}
  }
  window.ArkNoticeMarkdown=Object.freeze({render,applyColor,applyAppearance,expandVariables,highlightVariables});
})();
