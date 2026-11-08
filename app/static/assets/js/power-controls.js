"use strict";
(() => {
    let capability;
    const available=()=>capability||(capability=fetch('/api/system/power',{cache:'no-store'}).then(r=>r.ok?r.json():{}).then(v=>v.available===true).catch(()=>false));
    function open(){
        let popup=document.getElementById('ark-power-dialog');
        if(popup){popup.showModal();return;}
        popup=document.createElement('dialog');popup.id='ark-power-dialog';popup.className='ark-dialog-layout';popup.setAttribute('aria-labelledby','ark-power-heading');
        popup.innerHTML='<header class="ark-dialog-header"><h2 id="ark-power-heading">Power controls</h2></header><div class="ark-dialog-body"><label for="ark-power-operation">Action</label><select id="ark-power-operation" style="display:block;width:100%;margin:.5rem 0 1rem"><option value="restart">Restart</option><option value="shutdown">Shut down</option></select><p id="ark-power-explanation"></p><p>Everyone will be disconnected. Active downloads and other work will be interrupted.</p><p id="ark-power-result" role="status" aria-live="polite"></p></div><footer class="ark-dialog-footer"><button id="ark-power-confirm" type="button"></button><button id="ark-power-close" type="button">Close</button></footer>';
        document.body.append(popup);
        const select=popup.querySelector('select'),confirm=popup.querySelector('#ark-power-confirm'),result=popup.querySelector('#ark-power-result');
        function explain(){const off=select.value==='shutdown';confirm.textContent=off?'Shut down Data Ark':'Restart Data Ark';popup.querySelector('#ark-power-explanation').textContent=off?'Shut down this device safely before removing power. To use it again, someone must power it back on.':'Restart this device. The library and hotspot will return after it finishes booting.';}
        select.onchange=explain;explain();
        popup.querySelector('#ark-power-close').onclick=()=>popup.close();
        confirm.onclick=async()=>{
            const operation=select.value;confirm.disabled=true;select.disabled=true;
            try{
                const authorization=await CaretakerAuth.authorization('Authorize '+(operation==='shutdown'?'shutting down':'restarting')+' this Data Ark.');
                result.textContent='Requesting '+(operation==='shutdown'?'shutdown':'restart')+'…';
                const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),15000);
                let response;
                try{response=await fetch('/api/system/power',{method:'POST',headers:{Authorization:authorization,'Content-Type':'application/json'},body:JSON.stringify({operation,confirmed:true}),signal:controller.signal});}finally{clearTimeout(timer);}
                CaretakerAuth.rejected(response);
                const data=await response.json();if(!response.ok||!data.ok)throw Error(data.detail||'The power action could not be scheduled.');
                result.textContent=operation==='shutdown'?'Shutdown scheduled. Wait until the device has finished shutting down before removing power.':'Restart scheduled. Reconnect to the DataArk hotspot or reload the page after the device has restarted.';
                result.className='ark-dialog-notice';popup.dataset.queued='true';
            }catch(error){result.textContent=error.name==='AbortError'?'Request cancelled or no confirmation received. Check the device before trying again.':error.message;result.className='ark-dialog-notice error';}
            finally{if(popup.dataset.queued!=='true'){confirm.disabled=false;select.disabled=false;}}
        };
        popup.showModal();
    }
    window.ArkPower={addControls(parent){const button=document.createElement('button');button.type='button';button.textContent='Power…';button.hidden=true;button.setAttribute('aria-haspopup','dialog');button.onclick=open;parent.append(button);available().then(ok=>button.hidden=!ok);}};
})();
