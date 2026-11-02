"""Read-only first-party link, masthead and unreferenced-file inventory.

Unreferenced is a review candidate, never a deletion instruction. Dynamic routes,
vendor resources, compatibility aliases and downloaded publications need review.
"""
import argparse,json,re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin,urlsplit,unquote

class Page(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.ids=set();self.headers=[];self.in_header=0;self.brand=False;self.header_text=[]
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if d.get('id'):self.ids.add(d['id'])
        if tag=='header':self.in_header+=1
        if self.in_header and tag=='img' and any(s in d.get('src','') for s in ('dej-software-footer','dej_software_footer','dej_software_about_logo')):self.brand=True
        for key in ('href','src','poster','data-src'):
            if d.get(key):self.links.append((tag,key,d[key]))
        if d.get('srcset'):
            self.links.extend((tag,'srcset',v.strip().split()[0]) for v in d['srcset'].split(',') if v.strip() and not v.strip().startswith('data:'))
        if tag=='meta' and d.get('http-equiv','').lower()=='refresh':
            match=re.search(r'url=(.*)',d.get('content',''),re.I)
            if match:self.links.append((tag,'refresh',match[1].strip()))
    def handle_endtag(self,tag):
        if tag=='header':self.in_header=max(0,self.in_header-1)
    def handle_data(self,text):
        if self.in_header:self.header_text.append(text.strip())

def audit(root,origin,media=None,deployed_prefixes=()):
    root=Path(root).resolve();origin=origin.rstrip('/')+'/';host=urlsplit(origin).hostname
    aliases={host}
    if host in ('dejsoftware.com','www.dejsoftware.com'):aliases.update(['dejsoftware.com','www.dejsoftware.com'])
    pages={};incoming=Counter();missing=[];fragments=[];external=set();service_urls=set();deployment_routes=set();references=0;unbranded=[]
    def first_party(path):return not any(p in ('assets','vendor','node_modules','saved') for p in path.relative_to(root).parts)
    for path in root.rglob('*.html'):
        if not first_party(path):continue
        parser=Page()
        try:parser.feed(path.read_text(encoding='utf-8-sig'))
        except (OSError,UnicodeError):continue
        pages[path]=parser
        text=path.read_text(encoding='utf-8-sig')
        redirect=bool(re.search(r'http-equiv=["\']refresh',text,re.I))
        if not parser.brand and not redirect and 'class="ark-wordmark"' not in text and 'editions' not in path.relative_to(root).parts:unbranded.append({'file':path.relative_to(root).as_posix(),'header':' '.join(filter(None,parser.header_text))[:150]})
    for path,parser in pages.items():
        base=urljoin(origin,path.relative_to(root).as_posix())
        for tag,attr,raw in parser.links:
            if raw.startswith(('mailto:','tel:','javascript:','data:','blob:')):continue
            url=urlsplit(urljoin(base,raw));references+=1
            if url.scheme not in ('http','https'):continue
            if url.hostname not in aliases:external.add(url.geturl());continue
            if url.port!=urlsplit(origin).port and url.port not in (None,80,443):service_urls.add(url.geturl());continue
            relative=unquote(url.path).lstrip('/')
            if any(relative==p.strip('/') or relative.startswith(p.strip('/')+'/') for p in deployed_prefixes):deployment_routes.add(url.geturl());continue
            if relative.startswith(('api/','cdn-cgi/')):continue
            if relative.startswith('library-files/') and media:target=Path(media)/relative.removeprefix('library-files/')
            else:target=root/relative
            if target.is_dir():
                if (target/'index.html').is_file():target=target/'index.html'
                elif relative.startswith('library-files/'):continue
            if not target.is_file():missing.append({'source':path.relative_to(root).as_posix(),'target':url.path,'attribute':attr});continue
            incoming[target.resolve()]+=1
            if url.fragment and target in pages and unquote(url.fragment) not in pages[target].ids and not any(c in url.fragment for c in ('=','/','?')):
                dynamic=False
                for script in pages[target].links:
                    if script[:2]!=('script','src'):continue
                    js=root/urlsplit(urljoin(origin+target.relative_to(root).as_posix(),script[2])).path.lstrip('/')
                    if js.is_file() and url.fragment in js.read_text(encoding='utf-8',errors='replace'):dynamic=True;break
                if not dynamic:fragments.append({'source':path.relative_to(root).as_posix(),'target':url.path+'#'+url.fragment})
    # Capture CSS and literal script asset references when identifying candidates.
    for path in root.rglob('*'):
        if not path.is_file() or path.suffix not in ('.css','.js','.json','.html'):continue
        if any(part in ('saved','node_modules') for part in path.relative_to(root).parts):continue
        try:text=path.read_text(encoding='utf-8-sig')
        except (OSError,UnicodeError):continue
        for raw in re.findall(r'url\(["\']?([^\)"\']+)|["\']((?:/|\.\./|\./)?assets/[^"\'?#]+)',text):
            value=next((s for s in raw if s),'').strip()
            if value.startswith(('data:','http:','https:','#')):continue
            relative=urlsplit(urljoin(origin+path.relative_to(root).as_posix(),value)).path.lstrip('/')
            incoming[(root/unquote(relative)).resolve()]+=1
    candidates=[p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.suffix.lower() in ('.html','.css','.js','.png','.webp','.jpg','.svg') and not incoming[p.resolve()] and first_party(p)]
    return {'root':str(root),'pages':len(pages),'link_references':references,'missing':missing,'fragment_review':fragments,'masthead_review':unbranded,'unreferenced_first_party_candidates':sorted(candidates),'service_urls':sorted(service_urls),'deployment_routes':sorted(deployment_routes),'external_urls':sorted(external)}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--origin',required=True);p.add_argument('--media',type=Path);p.add_argument('--deployed-prefix',action='append',default=[]);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=audit(a.root,a.origin,a.media,a.deployed_prefix);a.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:len(v) if isinstance(v,list) else v for k,v in result.items() if k!='root'}))
