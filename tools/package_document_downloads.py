from pathlib import Path
import json,hashlib,zipfile,re,os,shutil
import argparse
parser=argparse.ArgumentParser(description='Package complete rendered website editions for GitHub Releases before replacing website archives.')
parser.add_argument('--edition');parser.add_argument('--website',required=True,type=Path);parser.add_argument('--output',required=True,type=Path);args=parser.parse_args()
web=args.website.resolve();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
history=json.loads((Path(__file__).resolve().parents[1]/'config/document-downloads.json').read_text(encoding='utf-8'))
base=history['base_url']
record=json.loads(json.dumps(history))
for kind in ['collection','feature']:
 source=web/'data-ark'/f'{kind}-catalogue.pdf';digest=hashlib.sha256(source.read_bytes()).hexdigest();name=f'data-ark-{kind}-catalogue-{digest[:12]}.pdf';shutil.copyfile(source,out/name);record['pdfs'][source.name]=base+name
for directory in sorted((web/'data-ark/editions').iterdir()):
 if not directory.is_dir() or (args.edition and directory.name!=args.edition):continue
 edition=directory.name;prefix='/data-ark/editions/'+edition+'/';archive=out/f'data-ark-handbook-{edition}.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as bundle:
  for source in sorted(directory.rglob('*')):
   if not source.is_file():continue
   rel=source.relative_to(directory).as_posix();data=source.read_bytes()
   if source.suffix=='.html':
    text=data.decode('utf-8-sig')
    def link(m):
     attr,url=m.groups();target=None
     if url.startswith(prefix):target=url[len(prefix):]
     elif url.startswith('/styles.css'):target='styles.css'
     elif url.startswith('/data-ark/'):target='https://www.dejsoftware.com'+url
     elif url.startswith('/') and not url.startswith('//'):target='https://www.dejsoftware.com'+url
     if target is None:return m.group(0)
     if not target.startswith('http'):
      target=os.path.relpath(target.split('?')[0] or '.',str(Path(rel).parent)).replace('\\','/')
      if url.endswith('/'):target=target.rstrip('/')+'/index.html'
     return attr+'="'+target+'"'
    text=re.sub(r'(href|src)="([^"]+)"',link,text);data=text.encode('utf-8')
   bundle.writestr(rel,data)
  bundle.writestr('styles.css',(web/'styles.css').read_bytes())
  bundle.writestr('index.html','<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Data Ark handbook '+edition+'</title><link rel="stylesheet" href="styles.css"><main class="wrap collection-document"><h1>Data Ark handbook</h1><p>Edition '+edition+'</p><ul>'+''.join('<li><a href="'+p+'/index.html">'+p.title()+'</a></li>' for p in ['handbook','collection','features','engineering','installation','bootstrap'])+'</ul>'+('<p><a href="docs/index.html">Complete handbook contents</a> · <a href="api/index.html">API reference</a></p>' if (directory/'docs').exists() else '')+'</main></html>')
  bundle.writestr('README.txt','Extract this entire ZIP, then open index.html. Its edition pages and stylesheet are bundled. External website links and Ark administration links require their respective connections.\n')
 digest=hashlib.sha256(archive.read_bytes()).hexdigest();final=archive.with_name(archive.stem+'-'+digest[:12]+archive.suffix);archive.replace(final);archive=final
 record['editions'][edition]={'url':base+archive.name,'filename':archive.name}
known={a['filename']:a for a in record['assets']}
for asset in sorted(out.iterdir()):
 if asset.suffix in ['.pdf','.zip']:known[asset.name]={'filename':asset.name,'size':asset.stat().st_size,'sha256':hashlib.sha256(asset.read_bytes()).hexdigest(),'url':base+asset.name}
record['assets']=sorted(known.values(),key=lambda a:a['filename'])
(out/'download-manifest.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
(out/'SHA256SUMS').write_text(''.join(a['sha256']+'  '+a['filename']+'\n' for a in record['assets']),encoding='utf-8')
print(json.dumps({'assets':[(a['filename'],a['size']) for a in record['assets']]},indent=2))
