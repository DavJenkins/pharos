/* The exposed hanging sign links to DEJ; content panels remain above it. */
(() => {
 const style=getComputedStyle(document.body);
 const match=style.backgroundImage.match(/url\(["']?(.*?)["']?\)/);
 if(!match)return;
 let link=document.getElementById('background-dej-link');
 if(!link){
  link=document.createElement('a');link.id='background-dej-link';link.href='https://www.dejsoftware.com/';link.target='_blank';link.rel='noopener noreferrer';link.setAttribute('aria-label','DEJ Software™ website (internet required)');link.title='Visit DEJ Software™ (internet required)';link.hidden=true;document.body.append(link);
 }
 const rules=document.createElement('style');rules.textContent='#background-dej-link{position:fixed;z-index:1;border-radius:8px}#background-dej-link:focus-visible{outline:3px solid #d4af37;outline-offset:4px;background:#203e5433}.ark-page,.network-settings-card,.documentation-shell{position:relative;z-index:2}';document.head.append(rules);
 const image=new Image();
 const offset=(value,space)=>value.endsWith('%')?space*parseFloat(value)/100:parseFloat(value)||0;
 function place(){
  const width=document.documentElement.clientWidth,height=window.innerHeight;
  const scale=Math.max(width/image.naturalWidth,height/image.naturalHeight);
  const current=getComputedStyle(document.body);
  const left=offset(current.backgroundPositionX,width-image.naturalWidth*scale)+93*scale;
  const top=offset(current.backgroundPositionY,height-image.naturalHeight*scale)+210*scale;
  const x=Math.max(0,left),y=Math.max(0,top),w=Math.min(width,left+171*scale)-x,h=Math.min(height,top+132*scale)-y;
  link.hidden=w<24||h<24;
  if(!link.hidden)Object.assign(link.style,{left:x+'px',top:y+'px',width:w+'px',height:h+'px'});
 }
 image.onload=place;image.src=match[1];window.addEventListener('resize',place);
})();

// Render the product name with the lighthouse's original blue lettering.
// Leave editable fields, code, filenames and the combined masthead artwork intact.
(() => {
 const css=document.createElement('style');
 css.textContent='.ark-data-wordmark{display:inline-block;position:relative;vertical-align:-.07em;line-height:1;width:4.896em;height:.68em;overflow:hidden;white-space:nowrap}.ark-data-wordmark>img{position:absolute!important;display:block!important;max-width:none!important;width:109.27778%!important;height:319.6%!important;left:-5.55556%;top:-192%;object-fit:fill!important}.ark-data-wordmark-copy{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}';
 document.head.append(css);
 function replace(node){
  if(!node.parentElement || node.parentElement.closest('script,style,title,textarea,input,select,option,code,pre,svg,[contenteditable],.ark-data-wordmark'))return;
  const text=node.nodeValue;if(!/\bData Ark\b/i.test(text))return;
  const fragment=document.createDocumentFragment();let start=0;
  for(const match of text.matchAll(/\bData Ark\b/gi)){
   fragment.append(document.createTextNode(text.slice(start,match.index)));
   const mark=document.createElement('span');mark.className='ark-data-wordmark';mark.setAttribute('role','img');mark.setAttribute('aria-label','Data Ark');
   const image=document.createElement('img');image.src='/assets/pharos-data-ark-clean.png';image.alt='';
   const copy=document.createElement('span');copy.className='ark-data-wordmark-copy';copy.textContent='Data Ark';
   mark.append(image,copy);fragment.append(mark);start=match.index+match[0].length;
  }
  fragment.append(document.createTextNode(text.slice(start)));node.replaceWith(fragment);
 }
 function scan(root){
  if(root.nodeType===3){replace(root);return;}
  const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT),nodes=[];while(walker.nextNode())nodes.push(walker.currentNode);nodes.forEach(replace);
 }
 scan(document.body);
 new MutationObserver(records=>records.forEach(record=>{
  if(record.type==='characterData')replace(record.target);
  else record.addedNodes.forEach(scan);
 })).observe(document.body,{childList:true,subtree:true,characterData:true});
})();
