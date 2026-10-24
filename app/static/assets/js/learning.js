document.querySelectorAll('[data-reader]').forEach(a=>{const u=new URL(location.href);u.port='8080';u.pathname='/';u.search='';u.hash=a.dataset.reader.split('#')[1]||'';a.href=u.href;});
