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
def inject(target):
 count=0
 for p in target.rglob('*.html'):
  if p.is_symlink() or 'assets' in p.relative_to(target).parts:continue
  text=p.read_text(encoding='utf-8');updated=brand_links(text)
  if 'background-sign-link.js' not in updated:updated=updated.replace('</body>',SCRIPT+'</body>')
  if updated!=text:p.write_text(updated,encoding='utf-8');count+=1
 return count
if __name__=='__main__':print('Brand links updated on',inject(Path(sys.argv[1])),'pages')
