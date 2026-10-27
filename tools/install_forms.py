#!/usr/bin/env python3
"""Install curated blank forms and templates. Explicit/manual operation; never accepts completed forms."""
import argparse, concurrent.futures, hashlib, html, io, json, re, subprocess, tempfile, urllib.request, zipfile
from datetime import datetime, timezone
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
CATALOGUE=ROOT/'deploy/reference/forms-catalogue.json'
CONTENT=Path('/mnt/storage/forms')
def atomic(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as f:
        temp=Path(f.name);f.write(data)
    temp.chmod(0o644);temp.replace(path)
def download(item):
    item=dict(item);item['checked_at']=datetime.now(timezone.utc).isoformat()
    extension='docx' if item['url'].endswith('docx') else 'pdf'
    item['filename']=item['group']+'/'+item['id']+'.'+extension
    destination=CONTENT/item['filename']
    try:
        req=urllib.request.Request(item['url'],headers={'User-Agent':'Mozilla/5.0 (DataArk blank form archive)'})
        with urllib.request.urlopen(req,timeout=45) as response:
            data=response.read(30*1024*1024+1);item['resolved_url']=response.url
        if len(data)>30*1024*1024: raise ValueError('Document exceeds 30 MiB limit')
        with tempfile.NamedTemporaryFile(suffix='.'+extension) as check:
            check.write(data);check.flush()
            if extension=='pdf':
                if not data.startswith(b'%PDF-'): raise ValueError('Publisher did not return a PDF')
                info=subprocess.check_output(['pdfinfo',check.name],text=True,stderr=subprocess.STDOUT)
                item['pages']=int(re.search(r'^Pages:\s+(\d+)',info,re.M)[1])
                form=re.search(r'^Form:\s+(.+)',info,re.M);item['pdf_form']=form[1] if form else 'unknown'
                text=subprocess.check_output(['pdftotext','-f','1','-l','1',check.name,'-'],text=True,stderr=subprocess.DEVNULL)
                if re.search(r'DRAFT AS OF|DRAFT - NOT FOR FILING',text,re.I): raise ValueError('Draft form excluded')
                if item['edition']=='Tax year 2025' and '2025' not in text: raise ValueError('Tax year was not verified in document')
                item['document_header']=' '.join(text.split())[:700]
            else:
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    if 'word/document.xml' not in archive.namelist(): raise ValueError('Not a Word document')
                    if any('vbaproject' in name.lower() for name in archive.namelist()): raise ValueError('Macro document excluded')
                    from xml.etree import ElementTree as ET
                    text=' '.join(ET.fromstring(archive.read('word/document.xml')).itertext())
                    if 'Standard Terms' not in text or 'Cover Page' not in text: raise ValueError('Complete cover page and terms not verified')
                    item['document_header']=' '.join(text.split())[:700]
        atomic(destination,data)
        item.update(status='installed',bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
    except Exception as error:
        item.update(status='unavailable',error=str(error))
        # A failed publisher check must not hide an earlier verified local copy.
        previous_path=CONTENT/'sources.json'
        if destination.is_file() and previous_path.is_file():
            previous=next((r for r in json.loads(previous_path.read_text()) if r['id']==item['id'] and r.get('sha256')==hashlib.sha256(destination.read_bytes()).hexdigest()),None)
            if previous: item={**previous,'last_check_error':str(error),'checked_at':item['checked_at']}
    print(item['status'],item['id'],item.get('error',''),flush=True)
    return item
STYLE='<style>body{font:17px system-ui;line-height:1.55;max-width:1000px;margin:24px auto;padding:0 18px;background:#fffaf1;color:#163b53}a{color:#075b91}li{margin:18px 0}small{display:block}summary{cursor:pointer;padding:10px}h2{border-bottom:2px solid #829bb0;padding-top:18px}</style>'
def index(records):
    esc=html.escape;parts=['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Forms and Templates — Data Ark</title>'+STYLE+'</head><body><a href="/">Data Ark library</a><h1>Forms and Templates</h1><p><a href="/pdf-forms.html">Fill a PDF on your device</a> · <a href="/printables.html">Household worksheets & printable paper</a> · <a href="/library-files/family-resources/index.html">More agreements & readiness forms</a></p><p>Blank forms and reusable templates, preserved for offline reading, printing and editing.</p><p>Download a copy to your own device before entering personal information. This public library does not collect or store completed forms.</p><p>Tax returns below are explicitly for <strong>tax year 2025</strong>. Other forms retain their publisher revision at retrieval. Check the required year, accepted edition and submission instructions before filing. Contract templates require the parties to choose the governing law and business terms.</p><p><a href="sources.json">Source URLs, retrieval dates, revisions and SHA-256 hashes</a> · <a href="/docs/20-Administration/Forms.html">Collection maintenance</a></p>']
    for group,title in [('tax','Tax forms and instructions'),('government','Other government forms'),('contracts','Contracts and agreement templates')]:
        installed=[r for r in records if r['group']==group and r['status']=='installed']
        parts.append('<h2>'+title+'</h2><ul>')
        if group=='contracts': parts.append('<p>Common Paper templates, CC BY 4.0. Complete cover pages and standard terms are preserved together. Download Word files to edit or print; the NDA is also available as a PDF. These are business agreements, not residential lease or personal loan forms.</p>')
        for r in installed:
            fmt='Word document — download to edit/print' if r['filename'].endswith('.docx') else str(r['pages'])+'-page PDF; '+('fillable fields detected' if r.get('pdf_form') in ('AcroForm','XFA') else 'printable; no interactive fields detected' if r.get('pdf_form')=='none' else 'form support: '+r.get('pdf_form','unknown'))
            parts.append('<li data-form-id="forms-'+esc(r['id'],quote=True)+'"><a data-form-file href="'+esc(r['filename'],quote=True)+'">'+esc(r['title'])+'</a><small>'+esc(r['edition'])+' · '+esc(fmt)+'</small><small>'+esc(r['note'])+'</small><details><summary>Source and document revision</summary><p>'+esc(r.get('document_header',''))+'</p><p>Retrieved '+esc(r['checked_at'])+' from <a href="'+esc(r['url'],quote=True)+'">publisher (internet required)</a>.</p></details></li>')
        parts.append('</ul>')
    unavailable=[r for r in records if r['status']!='installed']
    if unavailable:
        parts.append('<h2>Not downloaded</h2><p>These publisher downloads could not be verified. They are not part of the installed collection.</p><ul>')
        for r in unavailable:parts.append('<li>'+esc(r['title'])+' — '+esc(r['error'])+'; <a href="'+esc(r['url'],quote=True)+'">publisher (internet required)</a></li>')
        parts.append('</ul>')
    parts.append('<h2>Contract attribution</h2><p>© Common Paper and contributors. <a href="https://creativecommons.org/licenses/by/4.0/">Creative Commons Attribution 4.0</a>. Publisher documents are unmodified. <a href="cc-by-4.0.txt">Offline license text</a>. Source and license notices are retained in the documents.</p><script src="/assets/js/forms-availability.js"></script></body></html>')
    atomic(CONTENT/'index.html',''.join(parts).encode())
def register(records):
    import fcntl
    from app.services.manifest import load_manifest,atomic_write
    from tools.library_removal import serialize
    with Path('/var/lib/dataark/updates/worker.lock').open('a') as lock:
        __import__('tools.content_lock',fromlist=['acquire']).acquire(lock)
        data=load_manifest(ROOT/'dataark.yaml')
        if not any(r['id']=='forms-templates' for r in data['repositories']):
            data['repositories'].append({'id':'forms-templates','category':'content_sources','title':'Forms and Templates','description':'Blank tax and government forms, instructions and openly licensed contract templates. Tax years, revisions and sources are preserved.','collapse_assets':True,'update_policy':'manual','refresh_interval':'never','links':[{'title':'Browse local forms and templates','url':'/library-files/forms/index.html'}]})
        for r in records:
            if r['status']!='installed':continue
            identifier='forms-'+r['id']
            asset={'id':identifier,'repository_id':'forms-templates','category':'pdf_reference','title':r['title']+' — '+r['edition'],'relative_path':'forms/'+r['filename'],'service_endpoint':'/library-files/forms/'+r['filename'],'online_url':r['url'],'download_url':r['url'],'expected_hash':r['sha256'],'update_policy':'manual','refresh_interval':'never','source_note':r['note']+' Retrieved '+r['checked_at']}
            data['assets']=[a for a in data['assets'] if a['id']!=identifier]+[asset]
        atomic_write(ROOT/'dataark.yaml',serialize(data).encode())
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--register',action='store_true');args=parser.parse_args()
    if not CONTENT.parent.is_mount():raise SystemExit('The content SSD must be mounted')
    catalogue=json.loads(CATALOGUE.read_text())
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:records=list(pool.map(download,catalogue))
    atomic(CONTENT/'sources.json',(json.dumps(records,ensure_ascii=False,indent=2)+'\n').encode())
    req=urllib.request.Request('https://creativecommons.org/licenses/by/4.0/legalcode.txt',headers={'User-Agent':'DataArk'})
    with urllib.request.urlopen(req,timeout=30) as response: atomic(CONTENT/'cc-by-4.0.txt',response.read())
    index(records)
    if args.register:register(records)
    print('Installed',sum(r['status']=='installed' for r in records),'of',len(records),'documents')
if __name__=='__main__':main()
