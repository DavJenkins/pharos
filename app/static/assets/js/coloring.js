import {fillRegion} from './coloring-fill.js?v=c6b5ce9a9826dd04';
import * as pdfjs from '/assets/vendor/pdfjs/build/pdf.mjs';
pdfjs.GlobalWorkerOptions.workerSrc='/assets/vendor/pdfjs/build/pdf.worker.mjs';
const el=id=>document.getElementById(id),base=el('pdf-layer'),ink=el('ink-layer'),ctx=ink.getContext('2d',{willReadFrequently:true});
let pdf=null,documentTask=null,page=1,task=null,loading=null,busy=false,drawing=false,changed=false,history=[],pages=new Map(),last=null;
const status=text=>{el('load-status').textContent=text;};
function buttons(){for(const id of ['previous','next','page-number','pdf-file','book','blank','save','print','clear','tool','go-page'])el(id).disabled=busy;el('previous').disabled=busy||!pdf||page<=1;el('next').disabled=busy||!pdf||page>=pdf.numPages;el('page-number').disabled=busy||!pdf;el('go-page').disabled=busy||!pdf;el('page-number').max=pdf?.numPages||1;el('page-number').value=page;el('page-count').textContent=pdf?'of '+pdf.numPages:'';el('undo').disabled=busy||!history.length;}
function remember(){if(changed)pages.set(page,ink.toDataURL());else pages.delete(page);}
function checkpoint(){history.push({image:ctx.getImageData(0,0,ink.width,ink.height),changed});if(history.length>8)history.shift();changed=true;el('undo').disabled=false;}
async function show(n){if(busy)return;remember();busy=true;buttons();try{page=n;history=[];if(pdf){const p=await pdf.getPage(page),v=p.getViewport({scale:1}),scale=Math.min(2,1200/v.width,1600/v.height),viewport=p.getViewport({scale});base.width=ink.width=Math.ceil(viewport.width);base.height=ink.height=Math.ceil(viewport.height);task=p.render({canvasContext:base.getContext('2d'),viewport});await task.promise;task=null;p.cleanup();status('Page '+page+' of '+pdf.numPages+' — ready to color.');}else{base.width=ink.width=800;base.height=ink.height=1000;base.getContext('2d').fillStyle='white';base.getContext('2d').fillRect(0,0,800,1000);status('Blank page — choose a color and draw.');}ctx.clearRect(0,0,ink.width,ink.height);changed=pages.has(page);if(changed){const image=new Image();image.src=pages.get(page);await image.decode();ctx.drawImage(image,0,0);} }catch(e){status('Could not display this page: '+e.message);}finally{busy=false;buttons();}}
async function open(data){if(busy)return;if(changed||pages.size){if(!confirm('Opening another file clears this session’s paint. Save any colored pages first. Continue?'))return;}busy=true;buttons();status('Opening PDF…');try{if(documentTask)await documentTask.destroy();documentTask=null;pdf=null;pages.clear();changed=false;history=[];loading=pdfjs.getDocument({data,isEvalSupported:false,cMapUrl:'/assets/vendor/pdfjs/cmaps/',cMapPacked:true,standardFontDataUrl:'/assets/vendor/pdfjs/standard_fonts/',wasmUrl:'/assets/vendor/pdfjs/wasm/'});loading.onPassword=()=>{loading.destroy();status('This PDF needs a password. Open an unprotected coloring book instead.');};documentTask=loading;pdf=await loading.promise;loading=null;busy=false;await show(1);}catch(e){status('Could not open this PDF: '+e.message);busy=false;buttons();}}
el('pdf-file').onchange=async e=>{const f=e.target.files[0];if(!f)return;if(f.size>100*1024*1024){status('Choose a PDF smaller than 100 MB for this browser tool.');return;}await open(new Uint8Array(await f.arrayBuffer()));};
el('book').onchange=async()=>{const u=el('book').value;if(!u)return;try{status('Loading local book…');const r=await fetch(u);if(!r.ok)throw new Error('Book is no longer installed ('+r.status+')');await open(new Uint8Array(await r.arrayBuffer()));}catch(e){status(e.message);}};
fetch('/library-files/family-resources/sources.json').then(r=>r.json()).then(records=>{for(const r of records.filter(r=>r.status==='installed'&&r.collection==='kids'&&r.format==='pdf'&&!r.no_coloring_derivative))el('book').add(new Option(r.title+' · '+r.language,'/library-files/family-resources/'+r.filename));}).catch(()=>status('Library book list unavailable. You can still open your own PDF or draw.'));
el('blank').onclick=async()=>{if((changed||pages.size)&&!confirm('Clear this session’s paint and start a blank drawing?'))return;if(documentTask)await documentTask.destroy();documentTask=null;pdf=null;pages.clear();changed=false;el('tool').value='brush';await show(1);};
el('previous').onclick=()=>show(page-1);el('next').onclick=()=>show(page+1);const go=()=>{if(pdf)show(Math.max(1,Math.min(pdf.numPages,Number(el('page-number').value)||1)));};el('go-page').onclick=go;el('page-number').onkeydown=e=>{if(e.key==='Enter')go();};
function point(e){const r=ink.getBoundingClientRect();return [(e.clientX-r.left)*ink.width/r.width,(e.clientY-r.top)*ink.height/r.height];}
function fill(x,y){
  if(x<0||y<0||x>=ink.width||y>=ink.height)return;
  const composite=document.createElement('canvas');composite.width=base.width;composite.height=base.height;const c=composite.getContext('2d',{willReadFrequently:true});c.drawImage(base,0,0);c.drawImage(ink,0,0);const image=c.getImageData(0,0,ink.width,ink.height),p=image.data,W=ink.width,H=ink.height,offset=(Math.floor(y)*W+Math.floor(x))*4,target=Array.from(p.slice(offset,offset+3));
  if(target.every(v=>v<110)){status('Tap inside an area rather than on a dark outline.');return;}
  const rgb=el('paint-color').value.match(/\w\w/g).map(v=>parseInt(v,16)),paint=ctx.getImageData(0,0,W,H);
  const filled=fillRegion(p,paint.data,W,H,x,y,rgb,el('brush-size').value);
  if(!filled){status('The brush is too wide for this area. Try a smaller brush size.');return;}
  checkpoint();
  status('Area filled. Brush width controls which gaps the fill can pass through.');
  ctx.putImageData(paint,0,0);
}
ink.onpointerdown=e=>{if(busy)return;e.preventDefault();ink.setPointerCapture(e.pointerId);last=point(e);if(el('tool').value==='fill'){fill(...last);return;}checkpoint();drawing=true;stroke(last,last);};
function stroke(a,b){ctx.globalCompositeOperation=el('tool').value==='erase'?'destination-out':'source-over';ctx.strokeStyle=el('paint-color').value;ctx.lineWidth=Number(el('brush-size').value);ctx.lineCap='round';ctx.beginPath();ctx.moveTo(...a);ctx.lineTo(b[0]+.01,b[1]+.01);ctx.stroke();ctx.globalCompositeOperation='source-over';}
ink.onpointermove=e=>{if(!drawing)return;const p=point(e);stroke(last,p);last=p;};for(const name of ['onpointerup','onpointercancel','onlostpointercapture'])ink[name]=()=>drawing=false;
el('undo').onclick=()=>{const s=history.pop();if(!s)return;ctx.putImageData(s.image,0,0);changed=s.changed;buttons();};
el('clear').onclick=()=>{if(!changed)return;if(!confirm('Clear the paint on this page?'))return;checkpoint();ctx.clearRect(0,0,ink.width,ink.height);changed=false;};
function combined(){const c=document.createElement('canvas');c.width=base.width;c.height=base.height;const x=c.getContext('2d');x.drawImage(base,0,0);x.drawImage(ink,0,0);return c;}
el('save').onclick=()=>combined().toBlob(blob=>{const u=URL.createObjectURL(blob),a=document.createElement('a');a.href=u;a.download='ark-colored-page-'+page+'.png';a.click();setTimeout(()=>URL.revokeObjectURL(u),5000);});
el('print').onclick=async()=>{let s=el('print-sheet');if(!s){s=document.createElement('div');s.id='print-sheet';document.body.append(s);}const image=new Image();image.src=combined().toDataURL();await image.decode();s.replaceChildren(image);window.print();};
window.addEventListener('beforeunload',e=>{if(changed||pages.size){e.preventDefault();e.returnValue='';}});
el('tool').value='brush';show(1);
