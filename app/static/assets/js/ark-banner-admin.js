/* Caretaker-only banner editor, opened from the System status pop-up. */
(() => {
  'use strict';
  const $=selector=>document.querySelector(selector),dialog=$('#notice-dialog');
  if(!dialog)return;
  const form=$('#notice-form'),text=$('#notice-text'),picker=$('#notice-color'),hex=$('#notice-color-hex');
  const save=form.querySelector('[type=submit]'),clear=$('#clear-notice'),error=form.querySelector('.form-error');
  const mode=$('#notice-text-mode'),foreground=$('#notice-text-color'),width=$('#notice-width'),margin=$('#notice-margin');
  const settings=()=>({color:hex.value,text_color:mode.value==='auto'?'auto':foreground.value,width:width.value,margin:Number(margin.value)});
  let generation=0,busy=false;
  function preview() {
    const value=text.value,target=$('#notice-preview');
    window.ArkNoticeMarkdown.render(target,value);window.ArkNoticeMarkdown.applyAppearance(target,settings());
    foreground.disabled=busy||mode.value==='auto';margin.disabled=busy||width.value!=='margin';
    target.hidden=!value.trim();$('#notice-counter').textContent=value.length+' / 300';
  }
  function lock(value) {busy=value;for(const control of [text,picker,hex,mode,foreground,width,margin,save,clear])control.disabled=value;if(!value)preview();}
  async function request(value,password) {
    const options={cache:'no-store',headers:{}};
    if(value!==undefined) {
      options.method='POST';options.headers['Content-Type']='application/json';options.body=JSON.stringify(value);
      options.headers.Authorization='Basic '+btoa(String.fromCharCode(...new TextEncoder().encode('admin:'+password)));
    }
    const response=await fetch('/api/community/notice',options);
    let data;try{data=await response.json();}catch(_){throw Error('The Ark could not complete the request.');}
    if(!response.ok)throw Error(data.detail||'The Ark could not complete the request.');
    return data;
  }
  async function open() {
    const sequence=++generation;
    form.reset();form.elements.password.value='';error.textContent='';$('#notice-result').textContent='';
    preview();lock(true);dialog.showModal();
    try {
      const data=await request();if(sequence!==generation || !dialog.open)return;
      text.value=data.text;picker.value=/^#[0-9a-f]{6}$/i.test(data.color||'')?data.color:'#203e54';hex.value=picker.value;mode.value=data.text_color==='auto'?'auto':'custom';foreground.value=data.text_color==='auto'?'#d4af37':data.text_color||'#d4af37';width.value=data.width||'full';margin.value=data.margin??5;preview();
    }catch(failure){if(sequence===generation)error.textContent=failure.message;}
    finally {if(sequence===generation){lock(false);if(dialog.open)text.focus();}}
  }
  async function update(clearMessage) {
    if(busy || !form.reportValidity())return;
    error.textContent='';lock(true);
    try {
      await request({text:clearMessage?'':text.value,...settings()},form.elements.password.value);
      window.dispatchEvent(new Event('ark-notice-changed'));$('#notice-result').textContent=clearMessage?'The Ark banner has been cleared.':'The Ark banner has been saved.';
      dialog.close();
    }catch(failure){error.textContent=failure.message;}
    finally {lock(false);}
  }
  text.addEventListener('input',preview);for(const control of [mode,foreground,width,margin])control.addEventListener('input',preview);
  picker.addEventListener('input',()=>{hex.value=picker.value;preview();});
  hex.addEventListener('input',()=>{if(/^#[0-9a-f]{6}$/i.test(hex.value)){picker.value=hex.value;preview();}});
  form.addEventListener('submit',event=>{event.preventDefault();update(false);});
  clear.addEventListener('click',()=>update(true));
  $('#notice-close').addEventListener('click',()=>dialog.close());
  dialog.addEventListener('close',()=>{++generation;form.elements.password.value='';});
  window.ArkBannerAdmin=Object.freeze({open});
})();
