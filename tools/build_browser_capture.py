#!/usr/bin/env python3
"""Build the public capture page's target list and reproducible Chrome/helper package."""
import json,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.import_browser_reference import IDENTITY

def main():
 report=json.loads((ROOT/'deploy/reference/content-gaps.json').read_text(encoding='utf-8'))
 missing={x['id']:x for x in report['unavailable_entries']}
 metadata=json.loads((ROOT/'deploy/reference/capture-sources.json').read_text(encoding='utf-8'))['sources']
 if set(metadata)-set(IDENTITY): raise ValueError('Unknown capture source identity')
 targets=[]
 for group,folder in [('family','family-resources'),('forms','forms'),('resilience',None)]:
  for item in json.loads((ROOT/('deploy/reference/'+group+'-catalogue.json')).read_text(encoding='utf-8')):
   if item.get('format','pdf')=='pdf' and item['id'] in IDENTITY and metadata.get(item['id'],{}).get('disposition')!='retired':
    targets.append({'id':item['id'],'title':item['title'],'url':item['url'],'collection':folder or item['collection'],'source':metadata.get(item['id'],{})})
 source=ROOT/'tools/browser-capture';data=(json.dumps(targets,ensure_ascii=False,indent=2)+'\n').encode();(source/'targets.json').write_bytes(data)
 output=ROOT/'app/static/assets/downloads';output.mkdir(parents=True,exist_ok=True);(output/'capture-targets.json').write_bytes(data)
 names=['README.md','background.js','content.js','install.ps1','install.cmd','manifest.json','native_host.py','targets.json']
 with zipfile.ZipFile(output/'dataark-browser-capture.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
  for name in names:
   entry=zipfile.ZipInfo(name,(2026,10,24,0,0,0));entry.compress_type=zipfile.ZIP_DEFLATED;entry.external_attr=0o644<<16;archive.writestr(entry,(source/name).read_bytes())
 print('Built capture package for',len(targets),'approved PDF targets, including installed captures')
if __name__=='__main__':main()
