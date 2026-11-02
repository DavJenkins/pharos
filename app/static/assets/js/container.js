"use strict";
(()=>{
 const rewrite=()=>{
  for(const a of document.querySelectorAll('a[data-manifest-kiwix-port]')){
   const path=a.dataset.manifestKiwixPath||'/';const target='/kiwix/'+path.replace(/^\//,'');
   if(a.getAttribute('href')!==target)a.setAttribute('href',target);
  }
  for(const a of document.querySelectorAll('a[href]')){
   try{const u=new URL(a.href);if(u.hostname===location.hostname&&u.port==='8080'){const target='/kiwix'+u.pathname+u.search+u.hash;if(a.getAttribute('href')!==target)a.setAttribute('href',target);}}catch(e){}
  }
  for(const id of ['wifi-button','ap-button','pass-through-button','portal-continue']){const e=document.getElementById(id);if(e)e.hidden=true;}
  for(const a of document.querySelectorAll('a[href]')){
   if(['/config/wifi.html','/config/adapters.html','/config/https.html','/make-ark.html','/clone.html','/external-library.html','/storage.html','/recovery.html'].includes(a.getAttribute('href')))a.hidden=true;
   try{if(new URL(a.href).port==='4200')a.hidden=true;}catch(e){}
  }
 };
 function start(){
  const note=document.createElement('div');note.id='container-deployment';note.style.cssText='padding:.4rem .8rem;background:#203e54;color:#f5df9b;text-align:center;font:14px/1.5 system-ui';
  const label=document.createElement('span');label.textContent='Container edition · mounted library · host-managed network and storage · ';
  const link=document.createElement('a');link.href='/container.html';link.textContent='Container management';link.style.color='#8cdaff';note.append(label,link);document.body.prepend(note);
  rewrite();new MutationObserver(rewrite).observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['href']});
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();
