const form=document.getElementById('setup'),result=document.getElementById('result');
const readyText='<h2 class="setup-complete-title">Setup complete.</h2><ul class="setup-role-list"><li>For web administration, enter your caretaker password when prompted.</li><li>For SSH and terminal access, use <code>admin</code> with your Linux admin password.</li></ul><p class="setup-browsing-note">Browsing needs no password.</p>';
function showReady(){form.reset();form.hidden=true;const heading=document.querySelector('h1');if(heading)heading.hidden=true;['setup-introduction','setup-connection'].forEach(id=>{const hint=document.getElementById(id);if(hint)hint.hidden=true;});result.innerHTML=readyText;}
form.hidden=true;
form.querySelectorAll('[data-password-pair]').forEach(toggle=>{
 const [field,repeat]=toggle.dataset.passwordPair.split(' ').map(name=>form.elements.namedItem(name));
 let visible=false;
 toggle.addEventListener('click',()=>{
  visible=!visible;field.type=visible?'text':'password';repeat.disabled=visible;repeat.closest('label').hidden=visible;
  if(!visible)repeat.value='';
  toggle.setAttribute('aria-pressed',String(visible));
  const label=(visible?'Hide ':'Show ')+toggle.dataset.passwordLabel;
  toggle.setAttribute('aria-label',label);toggle.title=label;
 });
});
form.addEventListener('submit',async event=>{
 event.preventDefault();const data=new FormData(form);
 if((!form.elements.namedItem('repeat').disabled && data.get('password')!==data.get('repeat'))||(!form.elements.namedItem('admin_repeat').disabled && data.get('admin_password')!==data.get('admin_repeat'))){result.textContent='The passwords do not match.';return;}
 const button=form.querySelector('button[type="submit"]');button.disabled=true;result.textContent='Completing setup…';
 try{
  const response=await fetch('/api/recipient/setup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:data.get('code'),password:data.get('password'),admin_password:data.get('admin_password')})});
  const value=await response.json();if(!response.ok)throw new Error(value.detail||'Setup did not complete.');showReady();
 }catch(error){result.textContent=error.message;}finally{button.disabled=false;}
});
fetch('/api/recipient/status',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('Status unavailable');return r.json();}).then(d=>{
 if(d.setup_required===false){showReady();return;}
 if(d.setup_required!==true)throw new Error('Unexpected setup state');
 form.hidden=false;const intro=document.getElementById('setup-introduction');if(intro)intro.hidden=false;
 const p=document.getElementById('setup-connection');if(!p)return;
 p.hidden=false;p.textContent='Complete setup privately before inviting others to connect.';
}).catch(()=>{form.hidden=true;result.textContent='Unable to check setup status. Reload this page to try again.';});