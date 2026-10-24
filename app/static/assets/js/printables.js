(() => {
  'use strict';
  const byId=id=>document.getElementById(id),controls=['pattern','page-size','orientation','spacing','margin','weight','line-color'];
  for(const [id,name] of ArkPaper.patterns){const o=new Option(name,id);byId('pattern').add(o);}
  const sheet=document.createElement('div');sheet.id='print-sheet';document.body.append(sheet);
  const style=document.createElement('style');document.head.append(style);
  let current='',downloadUrl=null;
  function update(){
    let [w,h]=byId('page-size').value==='a4'?[210,297]:[215.9,279.4];
    if(byId('orientation').value==='landscape')[w,h]=[h,w];
    const number=(id,min,max,fallback)=>Math.min(max,Math.max(min,Number(byId(id).value)||fallback));
    current=ArkPaper.svg(byId('pattern').value,w,h,number('spacing',2,30,5),number('margin',5,35,12),byId('line-color').value,number('weight',.1,.8,.15));
    byId('paper-preview').innerHTML=current;sheet.innerHTML=current;if(downloadUrl)URL.revokeObjectURL(downloadUrl);downloadUrl=URL.createObjectURL(new Blob([current],{type:'application/octet-stream'}));byId('save-svg').href=downloadUrl;byId('save-svg').download='ark-'+byId('pattern').value+'.svg';style.textContent=`@page{size:${w}mm ${h}mm;margin:0}`;
  }
  for(const id of controls)byId(id).addEventListener('input',update);
  byId('print-paper').onclick=()=>{update();window.print();};
  update();
})();
