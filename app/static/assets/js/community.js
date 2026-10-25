/* All user content is rendered as text, never HTML or Markdown. */
(() => {
  'use strict';
  const $ = s => document.querySelector(s);
  const endpoint = '/api/community';
  let categories = {}, offset = 0, current = null, removal = null;
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
    if (password !== undefined) options.headers.Authorization=basic(password);
    const response=await fetch(endpoint+path,options);
    if (!response.ok) {
      let error; try { error=await response.json(); } catch (_) {}
      throw Error(error?.detail || 'The Ark could not complete the request. Try again shortly.');
    }
    return binary ? response.blob() : response.json();
  }
  function message(error) { $('#status').textContent=error ? error.message : ''; }
  function showReceipt(result) {
    $('#deletion-code').value=result.deletion_code; $('#copy-result').textContent=''; $('#receipt').showModal();
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
      $('#threads').append(link);
    }
    $('#page-info').textContent=result.total ? `${offset+1}–${Math.min(offset+50,result.total)} of ${result.total}` : '0 conversations';
    $('#previous').disabled=offset===0; $('#next').disabled=offset+50>=result.total;
  }
  function renderMessage(item, root) {
    const article=document.createElement('article'); article.className='message';
    if (root) article.append(text('h2',item.title),text('small',categories[item.category]||item.category));
    article.append(text('p',item.body,'message-body'));
    const footer=document.createElement('div');footer.className='message-footer';
    const remove=text('button','Remove…','remove-message');remove.type='button';
    remove.addEventListener('click',()=>{
      removal=item;$('#remove-form').reset();$('#remove .form-error').textContent='';
      $('#code-row').hidden=false;$('#password-row').hidden=true;
      $('#remove-note').textContent=root?'This permanently removes the post and all its replies. Daily backups may retain an earlier copy.':'This permanently removes this reply. Daily backups may retain an earlier copy.';
      $('#remove').showModal();
    });
    footer.append(text('small',`${item.name} · ${date(item.created_at)}`),remove);article.append(footer);return article;
  }
  async function navigate() {
    message();const match=location.hash.match(/^#thread=(\d+)$/);current=match?Number(match[1]):null;
    $('#list-panel').hidden=!!current;$('#thread-panel').hidden=!current;
    if (!current) return list();
    const data=await request('/threads/'+current);
    $('#conversation').replaceChildren(renderMessage(data.post,true),...data.replies.map(item=>renderMessage(item,false)));
  }
  async function refresh() { try { await navigate(); } catch(error) {message(error);} }
  for (const close of document.querySelectorAll('[data-close]')) close.addEventListener('click',()=>close.closest('dialog').close());
  for (const dialog of document.querySelectorAll('dialog')) dialog.addEventListener('close',()=>{
    for (const input of dialog.querySelectorAll('input[type=password]')) input.value='';
    if (dialog.id==='receipt') $('#deletion-code').value='';
  });
  $('#new-post').addEventListener('click',()=>{$('#post-form').reset();$('#post-form .form-error').textContent='';$('#compose').showModal();});
  $('#refresh').addEventListener('click',refresh);
  $('#category').addEventListener('change',()=>{offset=0;refresh();});
  $('#previous').addEventListener('click',()=>{offset=Math.max(0,offset-50);refresh();});
  $('#next').addEventListener('click',()=>{offset+=50;refresh();});
  $('#back').addEventListener('click',event=>{event.preventDefault();location.hash='';});
  $('#moderator').addEventListener('change',()=>{$('#password-row').hidden=!$('#moderator').checked;$('#code-row').hidden=$('#moderator').checked;});
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
  $('#reply-form').addEventListener('submit',event=>{event.preventDefault();const form=event.currentTarget;
    submit(form,async()=>{const result=await request('/threads/'+current+'/replies',Object.fromEntries(new FormData(form)));form.reset();showReceipt(result);await refresh();});
  });
  $('#remove-form').addEventListener('submit',event=>{event.preventDefault();const form=event.currentTarget;
    submit(form,async()=>{
      const moderator=$('#moderator').checked;
      const result=await request('/messages/'+removal.id+'/remove',moderator?{moderator:true}:{code:$('#remove-code').value.trim()},moderator?$('#password').value:undefined);
      $('#remove').close();if(!result.thread_id)location.hash='';else await refresh();
    });
  });
  $('#copy-code').addEventListener('click',async()=>{
    try {await navigator.clipboard.writeText($('#deletion-code').value);$('#copy-result').textContent='Code copied.';}
    catch (_) {$('#deletion-code').focus();$('#deletion-code').select();$('#copy-result').textContent='Code selected. Use Copy, or write it down.';}
  });
  $('#backup').addEventListener('click',()=>{$('#backup-form').reset();$('#backup-form .form-error').textContent='';$('#backup-dialog').showModal();});
  $('#backup-form').addEventListener('submit',event=>{event.preventDefault();const form=event.currentTarget;
    submit(form,async()=>{
      const blob=await request('/backup',{},form.elements.password.value,true),url=URL.createObjectURL(blob),a=document.createElement('a');
      a.href=url;a.download='dataark-community.sqlite3';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);$('#backup-dialog').close();
    });
  });
  window.addEventListener('hashchange',refresh);
  (async()=>{try {await list();await navigate();}catch(error){message(error);}})();

  function previewNotice() {
    const value=$('#notice-text').value;
    if(window.ArkNoticeMarkdown)window.ArkNoticeMarkdown.render($('#notice-preview'),value);else $('#notice-preview').textContent=value;$('#notice-preview').hidden=!value.trim();
    $('#notice-counter').textContent=value.length+' / 300';
  }
  $('#notice-text').addEventListener('input',previewNotice);
  $('#manage-notice').addEventListener('click',async()=>{
    const form=$('#notice-form');form.reset();form.querySelector('.form-error').textContent='';previewNotice();
    $('#notice-dialog').showModal();
    const button=form.querySelector('[type=submit]');button.disabled=true;
    try {const data=await request('/notice');$('#notice-text').value=data.text;previewNotice();}
    catch(error) {form.querySelector('.form-error').textContent=error.message;}
    finally {button.disabled=false;}
  });
  function saveNotice(clear) {
    const form=$('#notice-form');
    if(form.querySelector('[type=submit]').disabled || !form.reportValidity())return;
    submit(form,async()=>{
      await request('/notice',{text:clear?'':$('#notice-text').value},form.elements.password.value);
      $('#notice-dialog').close();window.dispatchEvent(new Event('ark-notice-changed'));
      $('#status').textContent=clear?'The Ark banner has been cleared.':'The Ark banner has been saved. Open landing pages update within a minute.';
    });
  }
  $('#notice-form').addEventListener('submit',event=>{event.preventDefault();saveNotice(false);});
  $('#clear-notice').addEventListener('click',()=>saveNotice(true));
})();
