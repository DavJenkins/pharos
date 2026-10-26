#!/usr/bin/env python3
"""Add the shared announcement client to deployed Ark HTML, including docs."""
from pathlib import Path
import hashlib,re,sys
ROOT=Path(__file__).resolve().parents[1]
def inject(target):
 count=0
 for page in target.rglob('*.html'):
  if page.is_symlink() or 'assets' in page.relative_to(target).parts:continue
  text=page.read_text();original=text
  # Regenerated docs and static files get one client, never a duplicate listener.
  if 'motd-notifications.js' in text:continue
  additions=[]
  if 'ark-notice.css' not in text:additions.append('<link rel="stylesheet" href="/assets/css/ark-notice.css?v='+hashlib.sha256((ROOT/'app/static/assets/css/ark-notice.css').read_bytes()).hexdigest()[:16]+'">')
  for script in ('assets/vendor/marked/marked.umd.js','assets/js/notice-markdown.js','assets/js/motd-notifications.js'):
   if script.split('/')[-1] not in text:
    version=hashlib.sha256((ROOT/'app/static'/script).read_bytes()).hexdigest()[:16]
    additions.append('<script src="/'+script+'?v='+version+'"></script>')
  block=''.join(additions)
  text=re.sub(r'</body>',lambda _:block+'</body>',text,count=1,flags=re.I) if re.search(r'</body>',text,re.I) else text+block
  if text!=original:page.write_text(text);count+=1
 return count
if __name__=='__main__':
 target=Path(sys.argv[1]).resolve()
 if target!=Path('/var/www/html'):raise SystemExit('Expected deployed Ark web root')
 print('MOTD notification client added to',inject(target),'HTML pages')
