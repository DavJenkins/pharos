#!/usr/bin/env python3
"""Link public DEJ branding; leave existing anchors, code and form values alone."""
from html.parser import HTMLParser
from pathlib import Path
import re,sys
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
 # Bring navigation into the shared masthead without changing page controls.
 if '<header class="ark-app-masthead">' not in text:
  text=re.sub(r'(<div class="ark-page-brand ark-shared-brand">.*?</div>)(\s*)(<nav\b[^>]*>.*?</nav>)',r'<header class="ark-app-masthead">\1\3</header>',text,flags=re.S)
  text=re.sub(r'(<div class="ark-page-brand ark-shared-brand">.*?</div>)(?!<nav)',lambda m:'<header class="ark-app-masthead">'+m[1]+'</header>' if '<header class="ark-app-masthead">' not in text else m[0],text,flags=re.S)
 if 'ark-shared-brand' in text and '/assets/css/ark-brand.css' not in text:
  text=text.replace('</head>','<link rel="stylesheet" href="/assets/css/ark-brand.css?v=1"></head>')
 text=re.sub(r'/assets/css/ark-brand.css\?v=[^"\s>]+','/assets/css/ark-brand.css?v=3',text)
 return text

def inject(target):
 count=0
 for p in target.rglob('*.html'):
  if p.is_symlink() or 'assets' in p.relative_to(target).parts:continue
  text=p.read_text(encoding='utf-8');updated=application_brand(brand_links(text))
  if 'background-sign-link.js' not in updated:updated=updated.replace('</body>',SCRIPT+'</body>')
  if 'dej-community-links.js' not in updated:updated=updated.replace('</body>','<script src="/assets/js/dej-community-links.js?v=1"></script></body>')
  if updated!=text:p.write_text(updated,encoding='utf-8');count+=1
 return count
if __name__=='__main__':print('Brand links updated on',inject(Path(sys.argv[1])),'pages')
