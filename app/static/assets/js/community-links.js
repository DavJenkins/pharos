/* Bookmark identifiers and private author codes belong only in the URL fragment. */
(() => {
  'use strict';
  const id=value=>/^[1-9][0-9]{0,9}$/.test(String(value)) && Number(value)<=2147483647?Number(value):null;
  const code=value=>typeof value==='string' && /^[A-Za-z0-9_-]{24}$/.test(value)?value:null;
  function parse(hash){const p=new URLSearchParams(hash.replace(/^#/,''));return {thread:id(p.get('thread')),message:id(p.get('message')),code:code(p.get('delete'))};}
  function link(thread,message,secret){
    if(!id(thread)||!id(message))throw Error('Invalid message bookmark.');
    const url=new URL('/community.html',location.href),p=new URLSearchParams({thread:String(thread),message:String(message)});
    if(secret!==undefined){if(!code(secret))throw Error('Invalid deletion code.');p.set('delete',secret);}
    url.hash=p.toString();return url.href;
  }
  window.ArkCommunityLinks=Object.freeze({parse,link});
})();
