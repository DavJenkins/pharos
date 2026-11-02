#!/usr/bin/env python3
"""Link public DEJ branding; leave existing anchors, code and form values alone."""
from html.parser import HTMLParser
from pathlib import Path
import re,sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.documentation_theme import online_notice
SCRIPT='<script src="/assets/js/background-sign-link.js?v=brand-links-2"></script>'
class BrandLinks(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=False);self.out=[];self.skipped=[]
 def handle_starttag(self,tag,attrs):
  self.out.append(self.get_starttag_text())
  if tag in ('a','code','pre','script','style','textarea','title'):self.skipped.append(tag)
 def handle_startendtag(self,tag,attrs):self.out.append(self.get_starttag_text())
 def handle_endtag(self,tag):
  self.out.append('</'+tag+'>')
  if self.skipped and self.skipped[-1]==tag:self.skipped.pop()
 def handle_data(self,text):
  self.out.append(text if self.skipped else re.sub(r'DEJ Software(?:™)?',lambda m:'<a href="https://www.dejsoftware.com/" title="DEJ Software website (internet required)">'+m[0]+'</a>',text,flags=re.I))
 def handle_entityref(self,name):self.out.append('&'+name+';')
 def handle_charref(self,name):self.out.append('&#'+name+';')
 def handle_decl(self,decl):self.out.append('<!'+decl+'>')
 def handle_comment(self,data):self.out.append('<!--'+data+'-->')
def brand_links(text):
 parser=BrandLinks();parser.feed(text);parser.close();return ''.join(parser.out)
def application_brand(text):
 # Only plain navigation labels are changed; filenames and code retain their spelling.
 labels={'/': {'Library':'Dashboard','Home':'Dashboard','Data Ark library':'Dashboard','Return to the library':'Return to Dashboard','Open the offline library':'Open Dashboard'}, '/index.html': {'Library':'Dashboard','Home':'Dashboard'}, '/library.html': {'Manage library':'Manage Library'}}
 def navigation(match):
  before,href,label,after=match.groups()
  return before+href+'">'+labels.get(href,{}).get(label,label)+after
 text=re.sub(r'(<a\b[^>]*href=")([^"<>]+)">([^<>]+)(</a>)',navigation,text)
 masthead='<div class="ark-page-brand ark-shared-brand"><a class="ark-maker" href="https://www.dejsoftware.com/" title="DEJ Software website (internet required)"><img src="/assets/dej-software-footer.webp" alt="DEJ Software™" width="1024" height="192"></a><a class="ark-home" href="/">Data Ark</a></div>'
 text=re.sub(r'<a class="ark-page-brand" href="/">Data Ark</a>',lambda m:masthead,text)
 # New first-party tools often start with navigation rather than the old brand
 # anchor. Give them the same masthead without changing their page title.
 if not any(marker in text for marker in ('ark-app-masthead','docs-masthead','class="docs-brand"','class="ark-wordmark"','id="pharos-title"','class="manifest-hero"')):
  if re.search(r'<header>\s*<a href="/">Data Ark</a>\s*</header>',text):
   text=re.sub(r'<header>\s*<a href="/">Data Ark</a>\s*</header>','<header class="ark-app-masthead">'+masthead+'</header>',text,count=1)
  elif re.search(r'<nav\b[^>]*>.*?</nav>',text,re.S):
   text=re.sub(r'<nav\b[^>]*>.*?</nav>',lambda m:'<header class="ark-app-masthead">'+masthead+m[0]+'</header>',text,count=1,flags=re.S)
  elif re.search(r'<header\b[^>]*>',text):
   text=re.sub(r'<header\b[^>]*>',lambda m:m[0]+'<div class="ark-app-masthead">'+masthead+'</div>',text,count=1)
 # Bring navigation into the shared masthead without changing page controls.
 if '<header class="ark-app-masthead">' not in text:
  text=re.sub(r'(<div class="ark-page-brand ark-shared-brand">.*?</div>)(\s*)(<nav\b[^>]*>.*?</nav>)',r'<header class="ark-app-masthead">\1\3</header>',text,flags=re.S)
  text=re.sub(r'(<div class="ark-page-brand ark-shared-brand">.*?</div>)(?!<nav)',lambda m:'<header class="ark-app-masthead">'+m[1]+'</header>' if '<header class="ark-app-masthead">' not in text else m[0],text,flags=re.S)
 if 'ark-shared-brand' in text and '/assets/css/ark-brand.css' not in text:
  stylesheet='<link rel="stylesheet" href="/assets/css/ark-brand.css?v=3">'
  text=text.replace('</head>',stylesheet+'</head>',1) if '</head>' in text else text.replace('<body',stylesheet+'</head><body',1)
 text=re.sub(r'/assets/css/ark-brand.css\?v=[^"\s>]+','/assets/css/ark-brand.css?v=3',text)
 return text

def inject(target):
 # A generated handbook references these shared assets. Install them together
 # with the HTML so partial deployments cannot create a hundred broken scripts.
 import shutil
 static=Path(__file__).resolve().parents[1]/'app/static'
 for relative in ['assets/js/dej-community-links.js','assets/dej-affiliations.webp','assets/css/ark-brand.css','assets/dej-software-footer.webp']:
  source=static/relative;destination=target/relative
  if source.resolve()!=destination.resolve():
   destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,destination);destination.chmod(0o644)
 count=0
 for p in target.rglob('*.html'):
  if p.is_symlink() or 'assets' in p.relative_to(target).parts:continue
  text=p.read_text(encoding='utf-8');updated=application_brand(brand_links(text))
  if 'background-sign-link.js' not in updated:updated=updated.replace('</body>',SCRIPT+'</body>')
  if 'dej-community-links.js' not in updated:updated=updated.replace('</body>','<script src="/assets/js/dej-community-links.js?v=1"></script></body>')
  counterparts={'content.html':'guides/content.html','resources.html':'guides/resources.html','legal/ifixit.html':'legal/ifixit.html'}
  counterpart=counterparts.get(p.relative_to(target).as_posix())
  if counterpart and 'docs-online-version' not in updated:
   updated=updated.replace('</main>',online_notice('https://www.dejsoftware.com/data-ark/'+counterpart)+'</main>',1)
  if updated!=text:p.write_text(updated,encoding='utf-8');count+=1
 return count
if __name__=='__main__':print('Brand links updated on',inject(Path(sys.argv[1])),'pages')
