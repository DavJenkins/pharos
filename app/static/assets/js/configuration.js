"use strict";
(() => {
    const el=id=>document.getElementById(id);
    let revision=null,saved='',validated=null,busy=false,communitySaved=true,leaving=false,currentFile='ark.yaml',generated=false,fileEntries=[];
    function message(text){el('configuration-result').textContent=text;}
    function lock(value){busy=value;for(const control of document.querySelectorAll('#configuration-controls button,#configuration-load,#community-enabled'))control.disabled=value;el('configuration-file').disabled=value;el('configuration-text').readOnly=value||generated;el('configuration-validate').disabled=value||generated;el('configuration-save').disabled=value||generated||validated!==el('configuration-text').value;}
    async function request(path,auth,data){const options={cache:'no-store',headers:{},signal:AbortSignal.timeout(20000)};if(auth)options.headers.Authorization=auth;if(data!==undefined){options.method='POST';options.headers['Content-Type']='application/json';options.body=JSON.stringify(data);}const response=await fetch('/api/configuration'+path,options);window.CaretakerAuth.rejected(response);const value=await response.json();if(!response.ok)throw Error(value.detail||'Configuration request failed.');return value;}
    function edited(){el('configuration-unsaved').hidden=el('configuration-text').value===saved;validated=null;el('configuration-save').disabled=true;el('configuration-preview').hidden=true;el('configuration-count').textContent=el('configuration-text').value.split('\n').length.toLocaleString()+' lines · '+el('configuration-text').value.length.toLocaleString()+' characters';window.ArkYamlHighlight?.refresh();}
    function setText(value){
        const editor=el('configuration-text');editor.value=value;editor.scrollTop=0;editor.scrollLeft=0;edited();
        const select=el('configuration-section'),sections=[...value.matchAll(/^([a-z_][a-z0-9_-]*):/gm)];
        select.replaceChildren();select.value='';select.disabled=sections.length<=1;
        if(sections.length!==1){const blank=document.createElement('option');blank.value='';blank.textContent=sections.length?'Choose a section…':'No sections';select.append(blank);}
        for(const match of sections){const option=document.createElement('option');option.value=String(match.index);option.textContent=match[1];select.append(option);}
        select.value=sections.length===1?String(sections[0].index):'';
    }
    function viewPath(file=currentFile){return file?'?file='+encodeURIComponent(file):'';}
    function renderFileTree(){
        const root={folders:new Map(),files:[]};
        for(const file of fileEntries){let branch=root;const parts=file.path.split('/');for(const folder of parts.slice(0,-1)){if(!branch.folders.has(folder))branch.folders.set(folder,{folders:new Map(),files:[]});branch=branch.folders.get(folder);}branch.files.push({...file,name:parts.at(-1)});}
        const tree=el('configuration-file-tree');tree.replaceChildren();
        function fileButton(file,parent){const button=document.createElement('button');button.type='button';button.textContent=file.name+(file.read_only?' (read-only)':'');button.setAttribute('aria-current',String((file.path||null)===currentFile));button.onclick=()=>{if(busy)return;el('configuration-file').value=file.path;el('configuration-file-browser').open=false;el('configuration-file').onchange();};parent.append(button);}
        function append(branch,parent,prefix=''){for(const file of branch.files)fileButton(file,parent);for(const [name,child] of branch.folders){const folder=document.createElement('details');const folderPath=prefix+name+'/';folder.open=!!currentFile&&currentFile.startsWith(folderPath);const summary=document.createElement('summary');summary.textContent=name+'/';folder.append(summary);append(child,folder,folderPath);parent.append(folder);}}
        append(root,tree);fileButton({path:'',name:'Combined compatibility snapshot (advanced)'},tree);
        el('configuration-file-current').textContent=currentFile||'Combined compatibility snapshot';
    }
    function loaded(value){revision=value.revision;currentFile=value.file??null;generated=!!value.read_only;el('configuration-active-file').textContent=(currentFile||'Combined compatibility snapshot')+(generated?' (read-only)':'');const picker=el('configuration-file');picker.replaceChildren();for(const file of value.files||[]){const option=document.createElement('option');option.value=file.path;option.textContent=file.path+(file.read_only?' (read-only)':'');picker.append(option);}const combined=document.createElement('option');combined.value='';combined.textContent='Combined compatibility snapshot (advanced)';picker.append(combined);picker.value=currentFile||'';fileEntries=value.files||[];renderFileTree();el('configuration-file-note').textContent=generated?'Generated snapshot (read-only).':currentFile?'':'Combined compatibility snapshot (advanced).';el('configuration-file-note').hidden=!el('configuration-file-note').textContent;saved=value.text;setText(saved);communitySaved=value.community_enabled;el('community-enabled').checked=communitySaved;el('configuration-controls').hidden=false;const select=el('configuration-history');select.replaceChildren();for(const item of value.history){const option=document.createElement('option');option.value=item.id;option.textContent=new Date(item.saved_at).toLocaleString();select.append(option);}el('configuration-restore').disabled=!value.history.length;message(value.project_warning||(value.status?.state==='error'?value.status.message:'Configuration loaded.'));}
    async function authorized(purpose,operation){if(busy)return;lock(true);try{const auth=await window.CaretakerAuth.authorization(purpose);await operation(auth);}catch(error){message(error.name==='AbortError'?'Action cancelled.':error.message);}finally{lock(false);}}
    async function readOnly(operation){if(busy)return;lock(true);try{await operation();}catch(error){message(error.message);}finally{lock(false);}}
    async function follow(auth,id){
        const deadline=Date.now()+450000;
        while(Date.now()<deadline){
            const response=await fetch('/api/configuration/status',{cache:'no-store'}),state=await response.json();
            if(state.id && state.id!==id)throw Error('Publication state changed. Reload the configuration.');
            message(state.message||'Publishing…');
            if(state.state==='ready'){loaded(await request(viewPath(),null));message('Configuration saved and published.');return;}
            if(state.state==='error'){const current=await request(viewPath(),null);throw Error(current.status?.message||state.message);}
            await new Promise(resolve=>setTimeout(resolve,1000));
        }
        throw Error('Publication is taking longer than expected. Reload to check its state before retrying.');
    }
    el('configuration-load').onclick=()=>{if(el('configuration-text').value!==saved&&!confirm('Discard unsaved YAML edits and reload?'))return;return readOnly(async()=>loaded(await request(viewPath(currentFile||'ark.yaml'),null)));};
    el('community-enabled').onchange=()=>{
        const enabled=el('community-enabled').checked;
        if(el('configuration-text').value!==saved){el('community-enabled').checked=!enabled;message('Save or reload your YAML edits before changing Community visibility.');return;}
        authorized('Change Community visibility.',async auth=>{const result=await request('/community',auth,{enabled,revision});await follow(auth,result.id);}).finally(()=>{el('community-enabled').checked=communitySaved;});
    };
    el('configuration-file').onchange=()=>{const file=el('configuration-file').value;if(el('configuration-text').value!==saved&&!confirm('Discard unsaved edits and switch files?')){el('configuration-file').value=currentFile||'';return;}return readOnly(async()=>{const previous=el('configuration-text').value,previousLabel=el('configuration-active-file').textContent;setText('');el('configuration-unsaved').hidden=true;el('configuration-active-file').textContent='Loading '+(file||'combined compatibility snapshot')+'…';el('configuration-file-current').textContent=file||'Combined compatibility snapshot';message('Loading configuration file…');try{loaded(await request(viewPath(file),null));}catch(error){setText(previous);el('configuration-active-file').textContent=previousLabel;el('configuration-file').value=currentFile||'';renderFileTree();throw error;}});};
    el('configuration-text').oninput=edited;
    el('configuration-validate').onclick=()=>readOnly(async()=>{const text=el('configuration-text').value;const value=await request('/validate',null,{text,...(currentFile?{file:currentFile}:{})});validated=text;const list=el('configuration-cards');list.replaceChildren();for(const card of value.cards){const li=document.createElement('li');li.textContent=card.title+(card.enabled?'':' (disabled)');list.append(li);}el('configuration-summary').textContent=value.assets.toLocaleString()+' asset definitions · '+value.categories+' categories · Community '+(value.community_enabled?'visible':'hidden')+'. Missing local content may be hidden by the manifest settings.';el('configuration-preview').hidden=false;message('YAML and manifest validation passed. Review the summary, then Save & publish.');});
    el('configuration-save').onclick=()=>{if(validated!==el('configuration-text').value)return;authorized('Save and publish the content configuration.',async auth=>{const result=await request('/save',auth,{text:el('configuration-text').value,revision,...(currentFile?{file:currentFile}:{})});await follow(auth,result.id);});};
    el('configuration-download').onclick=()=>{const link=document.createElement('a'),url=URL.createObjectURL(new Blob([el('configuration-text').value],{type:'text/yaml'}));link.href=url;link.download=currentFile?currentFile.replaceAll('/','-'):'dataark-content.yaml';link.click();setTimeout(()=>URL.revokeObjectURL(url),60000);};
    el('configuration-restore').onclick=()=>{const id=el('configuration-history').value;if(!id)return;return readOnly(async()=>{const value=await request('/history/'+encodeURIComponent(id),null);currentFile=null;generated=false;el('configuration-active-file').textContent='Previous combined snapshot';renderFileTree();el('configuration-file').value='';el('configuration-file-note').hidden=false;el('configuration-file-note').textContent='Previous combined snapshot. Validate and publish to restore the entire previous configuration.';setText(value.text);message('Previous combined version loaded. Validate and publish it to restore.');});};
    function selectAt(at,length=0){const editor=el('configuration-text');editor.focus();editor.setSelectionRange(at,at+length);editor.scrollTop=editor.value.slice(0,at).split('\n').length*21-80;}
    el('configuration-section').onchange=()=>{if(el('configuration-section').value!=='')selectAt(Number(el('configuration-section').value));};
    el('configuration-find-next').onclick=()=>{const value=el('configuration-find').value,editor=el('configuration-text');if(!value)return;const text=editor.value.toLowerCase();let at=text.indexOf(value.toLowerCase(),editor.selectionEnd);if(at<0)at=text.indexOf(value.toLowerCase());if(at<0)message('Text not found.');else selectAt(at,value.length);};
    el('configuration-close').onclick=event=>{if(el('configuration-text').value!==saved&&!confirm('Leave without saving your YAML edits?')){event.preventDefault();return;}leaving=true;};
    window.addEventListener('beforeunload',event=>{if(!leaving&&el('configuration-text').value!==saved){event.preventDefault();event.returnValue='';}});
})();
