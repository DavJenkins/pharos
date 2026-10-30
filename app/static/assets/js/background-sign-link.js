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
