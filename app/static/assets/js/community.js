/* Message Markdown uses the shared DOM-only renderer; names and titles stay text. */
(() => {
  'use strict';
  const $ = s => document.querySelector(s);
  const endpoint = '/api/community';
  let categories = {}, offset = 0, current = null, removal = null, editing = null, replyTarget = null;
  const links=window.ArkCommunityLinks;
  function text(tag, value, className) {
    const node = document.createElement(tag); node.textContent = value;
    if (className) node.className = className; return node;
  }
  function date(value) { return new Date(value).toLocaleString(); }
  function basic(password) {
    return 'Basic '+btoa(String.fromCharCode(...new TextEncoder().encode('admin:'+password)));
  }
  async function request(path, data, password, binary=false) {
    const options = {cache:'no-store', headers:{}};
    if (data !== undefined) {
      options.method='POST'; options.headers['Content-Type']='application/json'; options.body=JSON.stringify(data);
    }
    if (password !== undefined) options.headers.Authorization=basic(await window.CaretakerAuth.password('Authorize community board management.'));
    const response=await fetch(endpoint+path,options);
    window.CaretakerAuth.rejected(response);
    if (!response.ok) {
      let error; try { error=await response.json(); } catch (_) {}
      throw Error(error?.detail || 'The Ark could not complete the request. Try again shortly.');
    }
    return binary ? response.blob() : response.json();
  }
  function message(error) { $('#status').textContent=error ? error.message : ''; }
  function showReceipt(result) {
    $('#deletion-code').value=result.deletion_code;
    $('#receipt-public').href=links.link(result.thread_id,result.id);
    $('#private-link').value=links.link(result.thread_id,result.id,result.deletion_code);
    $('#open-private-link').href=$('#private-link').value; $('#copy-result').textContent=''; $('#receipt').showModal();
  }
  async function list() {
    const result=await request('/threads?category='+encodeURIComponent($('#category').value)+'&offset='+offset);
    categories=result.categories;
    if ($('#category').options.length===1) {
      for (const [id,label] of Object.entries(categories)) {
        $('#category').add(new Option(label,id)); $('#post-category').add(new Option(label,id));
      }
    }
    $('#threads').replaceChildren();
    if (!result.threads.length) $('#threads').append(text('p','No conversations here yet. Start one with New post.'));
    for (const thread of result.threads) {
      const link=document.createElement('a'); link.href='#thread='+thread.id; link.className='thread-link';
      link.append(text('strong',thread.title),text('small',`${categories[thread.category]} · ${thread.name} · ${date(thread.created_at)} · ${thread.replies} ${thread.replies===1?'reply':'replies'}`));
      if(thread.caretaker_edit)link.append(text('small','Edited by caretaker · '+date(thread.caretaker_edit.edited_at),'caretaker-edit'));
      $('#threads').append(link);
    }
    $('#page-info').textContent=result.total ? `${offset+1}–${Math.min(offset+50,result.total)} of ${result.total}` : '0 conversations';
    $('#previous').disabled=offset===0; $('#next').disabled=offset+50>=result.total;
  }
  function renderMessage(item, root) {
    const article=document.createElement('article'); article.className='message';
    if (root) article.append(text('h2',item.title),text('small',categories[item.category]||item.category));
    const body=text('div','','message-body message-markdown');window.ArkNoticeMarkdown.render(body,item.body);article.append(body);
    const footer=document.createElement('div');footer.className='message-footer';
    const remove=text('button','Remove…','remove-message');remove.type='button';
    remove.addEventListener('click',()=>openRemoval(item,root));
    const permalink=text('a','Permalink','message-permalink');permalink.href=links.link(current,item.id);permalink.title='Open or bookmark this message';
    article.id='message-'+item.id;
    const edit=text('button','Edit…','edit-message');edit.type='button';edit.title='Caretaker edit';edit.addEventListener('click',()=>{
      editing=item;$('#edit-form').reset();$('#edit-form .form-error').textContent='';$('#edit-title').value=item.title;$('#edit-title-row').hidden=!root;$('#edit-body').value=item.body;$('#edit-author').textContent='Posted by '+item.name+' · '+date(item.created_at);$('#edit-dialog').showModal();
    });
    if(item.caretaker_edit)article.append(text('p','Edited by caretaker · '+date(item.caretaker_edit.edited_at),'caretaker-edit'));
    const reply=text('button','Reply','reply-message');reply.type='button';reply.addEventListener('click',()=>{replyTarget=item.id;$('#reply-heading').textContent='Reply to '+item.name;$('#reply-context').textContent=item.body.slice(0,180);$('#reply-context').hidden=false;$('#reply-root').hidden=false;$('#reply-form').scrollIntoView({block:'start'});$('#reply-form textarea').focus();});
    footer.append(text('small',`${item.name} · ${date(item.created_at)}`),permalink,reply,edit,remove);article.append(footer);return article;
  }
  function openRemoval(item,root,code='') {
    removal=item;$('#remove-form').reset();$('#remove .form-error').textContent='';
    $('#code-row').hidden=false;$('#password-row').hidden=true;$('#remove-code').value=code;
    $('#remove-preview').textContent=(item.title?item.title+'\n':'')+item.name+' · '+date(item.created_at)+'\n\n'+item.body;
    $('#remove-note').textContent=root?'This permanently removes the post and all its replies. Daily backups may retain an earlier copy.':'This permanently removes this reply. Daily backups may retain an earlier copy.';
    if(!$('#remove').open)$('#remove').showModal();
  }
  async function navigate() {
    message();const bookmark=links.parse(location.hash);current=bookmark.thread;
    $('#list-panel').hidden=!!current;$('#thread-panel').hidden=!current;
    if (!current) return list();
    const data=await request('/threads/'+current);
    $('#conversation').replaceChildren(renderMessage(data.post,true));
    const containers=new Map(),rootReplies=text('div','','thread-replies');$('#conversation').append(rootReplies);containers.set(data.post.id,rootReplies);
    for(const item of data.replies){const branch=text('div','','thread-branch'),children=text('div','','thread-replies');branch.append(renderMessage(item,false),children);(containers.get(item.reply_to)||rootReplies).append(branch);containers.set(item.id,children);}
    if(![data.post,...data.replies].some(item=>item.id===replyTarget))resetReply();
    const selected=bookmark.message?[data.post,...data.replies].find(item=>item.id===bookmark.message):data.post;
    if(bookmark.message && !selected){$('#status').textContent='This message is no longer available. The rest of the conversation is shown below.';return;}
    if(bookmark.message){const article=document.getElementById('message-'+selected.id);article.classList.add('bookmarked-message');article.scrollIntoView({block:'center'});}
    if(bookmark.code && selected)openRemoval(selected,selected.id===data.post.id,bookmark.code);
  }
  async function refresh() { try { await navigate(); } catch(error) {message(error);} }
  for (const close of document.querySelectorAll('[data-close]')) close.addEventListener('click',()=>close.closest('dialog').close());
  for (const dialog of document.querySelectorAll('dialog')) dialog.addEventListener('close',()=>{
    for (const input of dialog.querySelectorAll('input[type=password]')) input.value='';
    if (dialog.id==='receipt') {$('#deletion-code').value='';$('#private-link').value='';$('#open-private-link').removeAttribute('href');}
    if(dialog.id==='remove')$('#remove-code').value='';
  });
  $('#new-post').addEventListener('click',()=>{$('#post-form').reset();$('#post-form .form-error').textContent='';$('#compose').showModal();});
  $('#refresh').addEventListener('click',refresh);
  $('#category').addEventListener('change',()=>{offset=0;refresh();});
  $('#previous').addEventListener('click',()=>{offset=Math.max(0,offset-50);refresh();});
  $('#next').addEventListener('click',()=>{offset+=50;refresh();});
  $('#back').addEventListener('click',event=>{event.preventDefault();location.hash='';});
  $('#moderator').addEventListener('change',()=>{$('#password-row').hidden=true;$('#code-row').hidden=$('#moderator').checked;});
  async function submit(form, operation) {
    const button=form.querySelector('[type=submit]');button.disabled=true;
    const errorNode=form.querySelector('.form-error');if(errorNode)errorNode.textContent='';
    try {await operation();} catch(error) {if(errorNode)errorNode.textContent=error.message;else message(error);} finally {button.disabled=false;}
  }
  $('#post-form').addEventListener('submit',event=>{event.preventDefault();const form=event.currentTarget;
    submit(form,async()=>{
      const result=await request('/threads',Object.fromEntries(new FormData(form)));
      $('#compose').close();form.reset();showReceipt(result);location.hash='thread='+result.thread_id;
    });
  });
  function resetReply(){replyTarget=null;$('#reply-heading').textContent='Reply to conversation';$('#reply-context').hidden=true;$('#reply-root').hidden=true;}
  $('#reply-root').addEventListener('click',resetReply);
  $('#reply-form').addEventListener('submit',event=>{event.preventDefault();const form=event.currentTarget;
    submit(form,async()=>{const result=await request('/messages/'+(replyTarget||current)+'/replies',Object.fromEntries(new FormData(form)));form.reset();resetReply();showReceipt(result);await refresh();});
  });
  $('#remove-form').addEventListener('submit',event=>{event.preventDefault();const form=event.currentTarget;
    submit(form,async()=>{
      const moderator=$('#moderator').checked;
      const result=await request('/messages/'+removal.id+'/remove',moderator?{moderator:true}:{code:$('#remove-code').value.trim()},moderator?$('#password').value:undefined);
      $('#remove').close();history.replaceState(null,'',result.thread_id?links.link(result.thread_id,result.thread_id):new URL('/community.html',location.href).href);await refresh();
    });
  });
  $('#copy-code').addEventListener('click',async()=>{
    try {await navigator.clipboard.writeText($('#deletion-code').value);$('#copy-result').textContent='Code copied.';}
    catch (_) {$('#deletion-code').focus();$('#deletion-code').select();$('#copy-result').textContent='Code selected. Use Copy, or write it down.';}
  });
  $('#copy-private-link').addEventListener('click',async()=>{
    const input=$('#private-link');
    try{await navigator.clipboard.writeText(input.value);$('#copy-result').textContent='Private link copied. Keep it to yourself.';}
    catch(_){input.focus();input.select();$('#copy-result').textContent='Private link selected. Use Copy, then save it somewhere private.';}
  });
  $('#receipt-public').addEventListener('click',event=>{event.preventDefault();const target=event.currentTarget.href;$('#receipt').close();location.href=target;});
  $('#open-private-link').addEventListener('click',event=>{event.preventDefault();const target=event.currentTarget.href;$('#receipt').close();location.href=target;});
  $('#edit-form').addEventListener('submit',event=>{event.preventDefault();const form=event.currentTarget;
    submit(form,async()=>{
      const result=await request('/messages/'+editing.id+'/edit',{title:$('#edit-title').value,body:$('#edit-body').value,previous_title:editing.title,previous_body:editing.body},form.elements.password.value);
      $('#edit-dialog').close();history.replaceState(null,'',links.link(result.thread_id,editing.id));await refresh();
    });
  });
  $('#backup').addEventListener('click',()=>{$('#backup-form').reset();$('#backup-form .form-error').textContent='';$('#backup-dialog').showModal();});
  $('#backup-form').addEventListener('submit',event=>{event.preventDefault();const form=event.currentTarget;
    submit(form,async()=>{
      const blob=await request('/backup',{},form.elements.password.value,true),url=URL.createObjectURL(blob),a=document.createElement('a');
      a.href=url;a.download='dataark-community.sqlite3';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);$('#backup-dialog').close();
    });
  });
  for(const formId of ['post-form','reply-form','edit-form']) {
    const form=document.getElementById(formId),input=form.querySelector('textarea');
    const tools=text('div','','markdown-tools'),help=document.createElement('details');help.className='markdown-help';
    help.append(text('summary','Formatting help'));
    for(const [syntax,description] of [['**bold**','Bold'],['*italic*','Italic'],['# Heading','Heading'],['- Item','Bullet list'],['1. Item','Numbered list'],['> Quote','Quoted text'],['[label](/community.html)','Link'],['`code`','Inline code'],['```\ncode\n```','Code block']]){const line=text('p','');line.append(text('code',syntax),document.createTextNode(' — '+description));help.append(line);}
    help.append(text('p','Blank lines separate paragraphs. Raw HTML is displayed as text. Images show their descriptions; they are not loaded.'));
    const button=text('button','Preview','markdown-preview-toggle');button.type='button';button.setAttribute('aria-expanded','false');
    const preview=text('div','','markdown-preview');preview.hidden=true;preview.id=formId+'-preview';button.setAttribute('aria-controls',preview.id);
    const body=text('div','','message-markdown');preview.append(text('h3','Preview'),body);
    const render=()=>window.ArkNoticeMarkdown.render(body,input.value||'Nothing to preview yet.');
    button.addEventListener('click',()=>{preview.hidden=!preview.hidden;button.textContent=preview.hidden?'Preview':'Hide preview';button.setAttribute('aria-expanded',String(!preview.hidden));if(!preview.hidden)render();});
    input.addEventListener('input',()=>{if(!preview.hidden)render();});
    form.addEventListener('reset',()=>{preview.hidden=true;button.textContent='Preview';button.setAttribute('aria-expanded','false');});
    tools.append(button,help);input.closest('label').after(tools,preview);
  }
  window.addEventListener('hashchange',refresh);
  (async()=>{try {await list();await navigate();}catch(error){message(error);}})();


  const restoreDialog=$('#restore-dialog'),restoreForm=$('#restore-form');
  let restoreToken=null,restoreBusy=false,restoreDone=false;
  function restoreReset() {
    restoreToken=null;restoreBusy=false;restoreDone=false;$('#restore-review').hidden=true;$('#restore-inputs').hidden=false;
    $('#restore-validate').hidden=false;$('#restore-validate').disabled=false;$('#restore-reselect').hidden=true;
    $('#restore-apply').hidden=true;$('#restore-apply').disabled=true;$('#restore-confirmation').checked=false;
    $('#restore-file').disabled=false;$('#restore-password').disabled=false;
  }
  function restoreLock(value) {
    restoreBusy=value;restoreDialog.querySelector('[data-close]').disabled=value;$('#restore-confirmation').disabled=value;
    for(const control of ['#restore-validate','#restore-reselect','#restore-file','#restore-password'])$(control).disabled=value;
    $('#restore-apply').disabled=value || !$('#restore-confirmation').checked;
  }
  $('#restore-board').addEventListener('click',()=>{
    restoreForm.reset();restoreReset();$('#restore-result').textContent='';$('#restore-form .form-error').textContent='';restoreDialog.showModal();
  });
  restoreDialog.addEventListener('cancel',event=>{if(restoreBusy)event.preventDefault();});
  restoreDialog.addEventListener('close',()=>{restoreToken=null;$('#restore-password').value='';});
  $('#restore-confirmation').addEventListener('change',()=>{$('#restore-apply').disabled=restoreBusy || !$('#restore-confirmation').checked;});
  $('#restore-reselect').addEventListener('click',()=>{restoreReset();$('#restore-result').textContent='';$('#restore-form .form-error').textContent='';});
  restoreForm.addEventListener('submit',async event=>{
    event.preventDefault();if(restoreToken || restoreDone || restoreBusy || !restoreForm.reportValidity())return;
    const file=$('#restore-file').files[0];if(!file)return;
    if(file.size>128*1024*1024){$('#restore-form .form-error').textContent='Backup exceeds 128 MiB.';return;}
    restoreLock(true);$('#restore-result').textContent='Uploading and validating backup…';$('#restore-form .form-error').textContent='';
    try {
      const response=await fetch(endpoint+'/restore/preview',{method:'POST',headers:{'Content-Type':'application/vnd.sqlite3',Authorization:await window.CaretakerAuth.authorization('Validate a community board backup.')},body:file,cache:'no-store'});
      window.CaretakerAuth.rejected(response);const data=await response.json();if(!response.ok)throw Error(data.detail||'Backup validation failed.');
      restoreToken=data.token;
      $('#restore-summary').textContent=`Backup: ${data.backup.posts} posts and ${data.backup.replies} replies. Current board: ${data.current.posts} posts and ${data.current.replies} replies.`+(data.backup.newest?' Newest backup message: '+date(data.backup.newest)+'.':'');
      $('#restore-banner').textContent=data.backup.banner?'Backup banner ('+data.backup.color+'): '+data.backup.banner:'The backup has no banner; restoring it clears the current banner.';
      $('#restore-review').hidden=false;$('#restore-validate').hidden=true;$('#restore-reselect').hidden=false;$('#restore-apply').hidden=false;
      $('#restore-result').textContent='Validated. Review and confirm below. This preview expires in ten minutes.';
    }catch(error){$('#restore-result').textContent='';$('#restore-form .form-error').textContent=error.message;}
    finally{restoreLock(false);if(restoreToken){$('#restore-file').disabled=true;$('#restore-password').disabled=true;}}
  });
  $('#restore-apply').addEventListener('click',async()=>{
    if(restoreBusy || !restoreToken || !$('#restore-confirmation').checked)return;
    restoreLock(true);$('#restore-result').textContent='Saving the current board, then restoring the reviewed backup…';$('#restore-form .form-error').textContent='';
    try {
      const data=await request('/restore/apply',{token:restoreToken,confirmation:'RESTORE'},$('#restore-password').value);
      restoreToken=null;restoreDone=true;$('#restore-password').value='';$('#restore-review').hidden=true;$('#restore-inputs').hidden=true;
      $('#restore-apply').hidden=true;$('#restore-reselect').hidden=true;$('#restore-validate').hidden=true;
      $('#restore-result').textContent=`Restored ${data.backup.posts} posts and ${data.backup.replies} replies. Previous board saved on the Pi as ${data.safety_backup}.`+(data.warning?' '+data.warning:'');
      window.dispatchEvent(new Event('ark-notice-changed'));location.hash='';await refresh();
    }catch(error){$('#restore-result').textContent='';$('#restore-form .form-error').textContent='Restore was not confirmed. Refresh the board to check its state before retrying. '+error.message;restoreReset();}
    finally{restoreLock(false);}
  });
})();
