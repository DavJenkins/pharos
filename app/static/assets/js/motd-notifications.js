/* Optional MOTD announcements for open Ark pages. No OS notification permission. */
(() => {
 'use strict';
 if(window.ArkMotdNotifications)return;
 const key='dataark.motd.lastNotification.v1';
 let seen=null,pending=null,dialog=null,content=null,shown=null,lastText='';
 try{seen=sessionStorage.getItem(key);}catch(_){}
 function acknowledge(id){seen=id;try{sessionStorage.setItem(key,id);}catch(_){}pending=null;}
 function redraw(){
  if(!dialog?.open||!shown)return;
  const now=new Date(),text=window.ArkNoticeMarkdown?.expandVariables(shown.text,now)||shown.text;
  if(text===lastText)return;lastText=text;
  if(window.ArkNoticeMarkdown)window.ArkNoticeMarkdown.render(content,shown.text,{variables:true,now});else content.textContent=shown.text;
 }
 function display(){
  if(!pending||document.hidden||document.querySelector('dialog[open]'))return;
  if(!dialog){
   dialog=document.createElement('dialog');dialog.id='ark-motd-popup';dialog.className='ark-motd-popup';dialog.setAttribute('aria-labelledby','ark-motd-popup-title');
   const title=document.createElement('h2');title.id='ark-motd-popup-title';title.textContent='Message of the day updated';
   content=document.createElement('div');content.className='ark-notice';
   const form=document.createElement('form');form.method='dialog';const close=document.createElement('button');close.type='submit';close.textContent='Close';form.append(close);dialog.append(title,content,form);document.body.append(dialog);
  }
  shown=pending;acknowledge(shown.notification_id);lastText='';
  window.ArkNoticeMarkdown?.applyAppearance(content,{...shown,position:'top',width:'full',margin_top:0,margin_bottom:0});
  dialog.showModal();redraw();dialog.querySelector('button').focus();
 }
 async function check(){
  try{
   const response=await fetch('/api/community/notice',{cache:'no-store'});if(!response.ok)return;
   const data=await response.json();if(typeof data.text!=='string')return;
   const id=typeof data.notification_id==='string'?data.notification_id:'';
   if(seen===null){acknowledge(id);return;} // Establish a baseline; do not alert a new visitor.
   if(!id){pending=null;return;}
   if(id!==seen&&data.text.trim()){pending=data;display();}
  }catch(_){/* Retry after transient connectivity loss. */}
 }
 window.addEventListener('ark-notice-saved',event=>acknowledge(event.detail?.notificationId||''));
 document.addEventListener('visibilitychange',()=>{display();check();});
 window.ArkMotdNotifications=Object.freeze({check});
 check();setInterval(check,10000);setInterval(()=>{display();redraw();},1000);
})();
