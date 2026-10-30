"""Publish the complete public handbook and a static API reference."""
from pathlib import Path
import html,json,re,shutil
from urllib.parse import urlsplit,unquote
from tools.publish_docs import markdown_to_html
ASSETS={'.json','.yaml','.yml','.txt','.pdf','.png','.jpg','.jpeg','.svg','.webp','.css'}

def inputs(root):
 paths=[p for p in (root/'docs').rglob('*') if p.is_file() and (p.suffix=='.md' or p.suffix in ASSETS)]
 paths+=list((root/'app/static/legal').glob('*.html'))
 paths += [root/'app/static/content.html',root/'app/static/resources.html']
 return sorted(paths)

def body(text):
 rendered=markdown_to_html(text);value=re.search(r'<main[^>]*>(.*?)</main>',rendered,re.S).group(1)
 value=re.sub(r'^<p class="docs-eyebrow">.*?</p>','',value,count=1)
 return re.sub(r'<p>\*(.*?)\*</p>',r'<p><em>\1</em></p>',value)

def rewrite(root,source,value,prefix,local=False,selected=None):
 selected=selected or {}
 def transform(match):
  attribute=match.group(1);raw=html.unescape(match.group(2));url=urlsplit(raw)
  if url.scheme or url.netloc or not url.path:return match.group(0)
  path=unquote(url.path);target=None;device=False
  if Path(path).name in ['collection-catalogue.pdf','feature-catalogue.pdf']:
   target='/'+Path(path).name if local else prefix+Path(path).name
  elif path in ['/api/docs','/api/redoc']:
   target='/api/docs' if local else prefix+'api/'
  elif path=='/api/openapi.json':target='/docs/30-Developer/api/openapi.json' if local else prefix+'api/openapi.json'
  else:
   candidate=(root/path.lstrip('/')) if path.startswith('/') else (source.parent/path).resolve()
   if path.startswith('/docs/'):candidate=root/path.lstrip('/')
   md=candidate.with_suffix('.md') if candidate.suffix in ['.html','.md'] else candidate
   if candidate.suffix in {'.html','.md'} and md.is_relative_to(root/'docs') and md.is_file():
    rel=md.relative_to(root/'docs').with_suffix('.html').as_posix()
    target='/docs/'+rel if local else selected.get(str(md.resolve()),prefix+'docs/'+rel)
   elif candidate.is_relative_to(root/'docs') and candidate.is_file():
    rel=candidate.relative_to(root/'docs').as_posix();target='/docs/'+rel if local else prefix+'docs/'+rel
   elif (path.startswith('/legal/') or candidate.is_relative_to(root/'legal')) and candidate.suffix.lower() in {'.crt','.pem'}:
    target=path if local else 'http://dataark'+path;device=not local
   elif path.startswith('/legal/') or candidate.is_relative_to(root/'legal'):
    rel=path.removeprefix('/legal/') if path.startswith('/legal/') else candidate.relative_to(root/'legal').as_posix();target='/legal/'+rel if local else prefix+'legal/'+rel
   elif path in ['/content.html','/resources.html']:target=path if local else prefix+'guides/'+Path(path).name
   elif path.startswith('/'):
    target=path if local else 'http://dataark'+path;device=not local
  if target is None:
   # A documentation-relative link that isn't a handbook file may be a
   # source-code reference; preserve it through the repository URL.
   if not path.startswith('/') and candidate.is_relative_to(root) and candidate.exists():
    target='https://github.com/DavJenkins/pharos/'+('blob' if candidate.is_file() else 'tree')+'/feature/readme-foundation/'+candidate.relative_to(root).as_posix()
   else:target=raw.split('#')[0].split('?')[0]
  if url.query:target+='?'+url.query
  if url.fragment:target+='#'+url.fragment
  return attribute+'="'+html.escape(target,quote=True)+'"'+(' title="Open on your Ark" data-on-ark="true"' if device and attribute=='href' else '')
 return re.sub(r'(href|src)="([^"]+)"',transform,value)

def api_body(schema,schema_url,contents):
 parts=['<h1>Data Ark API reference</h1><p>The HTTP contract shipped with this software edition. <a href="'+schema_url+'">Download OpenAPI JSON</a> · <a href="'+contents+'">Handbook contents</a></p><p><a href="http://dataark/api/docs" title="Open on your Ark">Interactive reference on your Ark</a>. Protected operations use the caretaker or integration authorization described in the administrator guides.</p>']
 operations=[]
 for path,entry in schema.get('paths',{}).items():
  for method,operation in entry.items():
   if method.lower() not in {'get','post','put','patch','delete','head','options'}:continue
   anchor=re.sub(r'[^a-z0-9]+','-',method+'-'+path.lower()).strip('-');operations.append((path,method,operation,anchor))
 parts.append('<nav class="api-endpoints" aria-label="API endpoints">'+''.join('<a href="#'+a+'"><code>'+html.escape(m.upper()+' /api'+p)+'</code></a>' for p,m,o,a in operations)+'</nav>')
 for path,method,operation,anchor in operations:
  parts+=['<section id="'+anchor+'"><h2>'+html.escape(method.upper()+' /api'+path)+'</h2>','<p>'+html.escape(operation.get('summary',''))+'</p>']
  if operation.get('description'):parts.append('<p>'+html.escape(operation['description'])+'</p>')
  parts.append('<details><summary>Parameters, request and responses</summary><pre><code>'+html.escape(json.dumps(operation,indent=2,ensure_ascii=False))+'</code></pre></details></section>')
 parts.append('<h2 id="schemas">Data models</h2>')
 for name,model in schema.get('components',{}).get('schemas',{}).items():parts.append('<details><summary>'+html.escape(name)+'</summary><pre><code>'+html.escape(json.dumps(model,indent=2,ensure_ascii=False))+'</code></pre></details>')
 return ''.join(parts)

def publish(root,web,archive,edition,config,frame):
 root=root.resolve();count=0
 for target,prefix in [(web,'/data-ark/'),(archive,'/data-ark/editions/'+edition+'/')]:
  docs=target/'docs';docs.mkdir(exist_ok=True)
  selected={str((root/p['source']).resolve()):prefix+p['id']+'/' for p in config['pages']}
  for source in sorted((root/'docs').rglob('*')):
   if not source.is_file():continue
   rel=source.relative_to(root/'docs');out=docs/rel
   if source.suffix=='.md':
    out=out.with_suffix('.html');text=source.read_text(encoding='utf-8-sig');title=next((line[2:] for line in text.splitlines() if line.startswith('# ')),source.stem)
    content='<p><a href="'+prefix+'docs/">Handbook contents</a></p>'+rewrite(root,source,body(text),prefix,selected=selected)
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(frame(title,content,prefix+'docs/'+rel.with_suffix('.html').as_posix(),prefix),encoding='utf-8')
   elif source.suffix in ASSETS:out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,out)
  (docs/'index.html').write_text((docs/'SUMMARY.html').read_text(encoding='utf-8'),encoding='utf-8')
  schema=json.loads((root/'docs/30-Developer/api/openapi.json').read_text(encoding='utf-8-sig'));api=target/'api';api.mkdir(exist_ok=True)
  (api/'index.html').write_text(frame('Data Ark API reference',api_body(schema,prefix+'api/openapi.json',prefix+'docs/'),prefix+'api/',prefix),encoding='utf-8');shutil.copyfile(root/'docs/30-Developer/api/openapi.json',api/'openapi.json')
  for source in list((root/'app/static/legal').glob('*.html'))+[root/'app/static/content.html',root/'app/static/resources.html']:
   text=source.read_text(encoding='utf-8-sig');match=re.search(r'<main[^>]*>(.*?)</main>',text,re.S)
   if not match:continue
   content=re.sub(r'<script\b[^>]*>.*?</script>','',match.group(1),flags=re.S|re.I);content=re.sub(r'<a class="ark-page-brand"[^>]*>.*?</a>','',content)
   content=rewrite(root,source,content,prefix,selected=selected)
   title=re.search(r'<h1[^>]*>(.*?)</h1>',content,re.S).group(1)
   rel=('legal/' if source.parent.name=='legal' else 'guides/')+source.name;out=target/rel;out.parent.mkdir(exist_ok=True);out.write_text(frame(html.unescape(re.sub('<[^>]+>','',title)),content,prefix+rel,prefix),encoding='utf-8')
  count=len(list((root/'docs').rglob('*.md')))
 return count
