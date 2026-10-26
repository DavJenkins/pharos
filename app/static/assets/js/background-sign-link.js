/* Align the transparent link with the sign in the fixed, centered cover image. */
(() => {
  const link=document.getElementById('background-dej-link');
  if(!link)return;
  const image=new Image();
  const match=getComputedStyle(document.body).backgroundImage.match(/url\(["']?(.*?)["']?\)/);
  if(!match)return;
  function place(){
    const width=document.documentElement.clientWidth,height=window.innerHeight;
    const scale=Math.max(width/image.naturalWidth,height/image.naturalHeight);
    const left=(width-image.naturalWidth*scale)/2+93*scale;
    const top=(height-image.naturalHeight*scale)/2+210*scale;
    const right=left+171*scale,bottom=top+132*scale;
    const visibleLeft=Math.max(0,left),visibleTop=Math.max(0,top);
    const visibleWidth=Math.min(width,right)-visibleLeft,visibleHeight=Math.min(height,bottom)-visibleTop;
    link.hidden=visibleWidth<24||visibleHeight<24;
    if(!link.hidden)Object.assign(link.style,{left:visibleLeft+'px',top:visibleTop+'px',width:visibleWidth+'px',height:visibleHeight+'px'});
  }
  image.onload=place;image.src=match[1];window.addEventListener('resize',place);
})();
