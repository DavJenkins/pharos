/* Shared DEJ footer links. Artwork is local; external services open only on request. */
(()=>{
 function attach(){
  // A discreet novelty in Help/About, never a recurring promotion.
  if(!/(?:^|\/)(?:help\/(?:index\.html)?|docs\/(?:index\.html|summary\.html)?|docs\/00-Introduction\/Welcome\.html|about\/handbook\/(?:index\.html)?)$/.test(location.pathname))return;
  if(document.querySelector('[data-dej-community-links]'))return;
  const source=document.currentScript?.src||Array.from(document.scripts).find(s=>s.src.includes('dej-community-links.js'))?.src;
  if(!source)return;
  const style=document.createElement('style');
  style.textContent='.dej-community-links{display:flex!important;flex-wrap:wrap;align-items:center;justify-content:center;gap:12px 24px;padding:12px 18px;box-sizing:border-box;color:#f8f1dc;background:#172d40;border:1px solid #b8943e;border-radius:8px;max-width:100%;font:14px/1.5 system-ui,Arial,sans-serif}.dej-community-links a{display:inline-flex;align-items:center;justify-content:center;min-height:44px;color:#f0cc6b!important;text-decoration:underline;text-underline-offset:3px}.dej-community-links a:focus-visible{outline:3px solid #68cdff;outline-offset:4px}.dej-community-links .dej-hello img{display:block;width:160px;max-width:100%;height:auto;max-height:none;object-fit:contain}.dej-community-links .dej-coffee{text-align:center}.dej-community-links small{display:block;color:#e2e9ef;font-size:11px}.dej-community-links .dej-coffee a{padding:0 8px}.dej-support-footer{position:relative;z-index:2;clear:both;width:min(1100px,calc(100% - 32px));margin:24px auto}.dej-support-footer .dej-community-links{margin:auto;width:fit-content}footer:has(>.dej-community-links){flex-wrap:wrap}@media(max-width:420px){.dej-community-links{gap:8px 16px;padding:10px 12px}.dej-community-links .dej-hello img{width:140px}}';
  document.head.append(style);
  const links=document.createElement('div');links.className='dej-community-links';links.dataset.dejCommunityLinks='';links.setAttribute('aria-label','DEJ Software community and optional support');
  const hello=document.createElement('a');hello.className='dej-hello';hello.href='mailto:support@DEJSoftware.com?subject=DEJ%20Software%20%E2%80%94%20Recognized%20one!';hello.setAttribute('aria-label','Recognize one? Say hello by email.');hello.title='Recognize one? Say hello.';
  const image=document.createElement('img');image.src=new URL('../dej-affiliations.webp',source).href;image.alt='DEJ Software affiliations — Recognize one? Say hello.';image.width=512;image.height=256;hello.append(image);
  const coffee=document.createElement('div');coffee.className='dej-coffee';const support=document.createElement('a');support.href='https://buymeacoffee.com/dejsoftware';support.target='_blank';support.rel='noopener noreferrer';support.textContent='Buy Dave a coffee ↗';const note=document.createElement('small');note.textContent='Optional support · internet required';coffee.append(support,note);links.append(hello,coffee);
  let footer=document.querySelector('footer:not([hidden]):not(.platform-credit)');
  if(!footer){footer=document.createElement('footer');footer.className='dej-support-footer';document.body.append(footer);}
  const disclosure=document.createElement('details');const heading=document.createElement('summary');heading.textContent='A personal note';disclosure.append(heading,links);footer.append(disclosure);
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',attach,{once:true});else attach();
})();
