"use strict";
document.getElementById('reload').onclick=async()=>{
 const result=document.getElementById('result');
 try{const authorization=await window.CaretakerAuth.authorization('Reload this container’s public configuration and library.');const r=await fetch('/api/container/reload',{method:'POST',headers:{authorization}});const d=await r.json();if(!r.ok)throw Error(d.detail||'Reload failed');result.textContent=d.message;}catch(e){result.textContent=e.message;}
};
