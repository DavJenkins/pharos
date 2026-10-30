"""Clarify the Kiwix welcome-page catalogue filter, leaving article search intact."""
import argparse,os,re,subprocess,tempfile,time,urllib.request
from pathlib import Path
BEGIN='<!-- DATAARK CATALOGUE FILTER BEGIN -->'
END='<!-- DATAARK CATALOGUE FILTER END -->'
SCRIPT='''<script>
(function(){
 function clarify(){
  const field=document.getElementById('searchFilter'),button=document.getElementById('searchButton'),body=document.querySelector('.kiwixHomeBody');
  if(!field||!button||!body)return;
  if(field.placeholder!=='Filter archives')field.placeholder='Filter archives';
  field.setAttribute('aria-label','Filter archive titles and descriptions');field.setAttribute('aria-describedby','ark-catalogue-filter-help');
  if(button.value!=='Filter')button.value='Filter';
  if(!document.getElementById('ark-catalogue-filter-help')){const note=document.createElement('p');note.id='ark-catalogue-filter-help';note.textContent='Filters archive titles and descriptions—not their contents. Open an archive to search within it.';note.style.cssText='margin:1rem 0;font:14px/1.5 roboto,system-ui,sans-serif;color:#243a4b';body.prepend(note);}
 }
 document.addEventListener('DOMContentLoaded',clarify);clarify();
 new MutationObserver(clarify).observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['placeholder','value']});
})();
</script>'''
def render(page):
 page=re.sub(re.escape(BEGIN)+'.*?'+re.escape(END)+r'\r?\n?','',page,flags=re.S)
 if 'id="searchFilter"' not in page or 'id="searchButton"' not in page or '</body>' not in page:raise ValueError('Unrecognized Kiwix catalogue page; existing page was not changed.')
 return page.replace('</body>',BEGIN+SCRIPT+END+'\n</body>',1)
def install(root=Path('/mnt/storage')):
 if not root.is_mount():raise ValueError('Content drive is not mounted')
 for attempt in range(30):
  try:
   with urllib.request.urlopen('http://127.0.0.1:8080/',timeout=5) as r:page=r.read(2*1024**2).decode('utf-8')
   break
  except OSError:
   if attempt==29:raise
   time.sleep(.5)
 folder=root/'.dataark-reader'
 if folder.is_symlink():raise ValueError('Reader configuration cannot be a symlink')
 folder.mkdir(exist_ok=True);folder.chmod(0o755)
 path=folder/'catalogue-index.html'
 if path.is_symlink():raise ValueError('Catalogue page cannot be a symlink')
 data=render(page).encode()
 with tempfile.NamedTemporaryFile(dir=folder,delete=False) as f:f.write(data);temp=Path(f.name)
 temp.chmod(0o644);temp.replace(path)
 return path
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apply',action='store_true');p.add_argument('--restart',action='store_true');a=p.parse_args()
 if not a.apply:p.error('Use --apply to write the catalogue welcome page')
 print(install())
 if a.restart:subprocess.run(['docker','restart','kiwix-serve'],check=True)
