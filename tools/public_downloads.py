"""Keep readable current pages on the website and stage versioned downloads for Releases."""
from pathlib import Path
import html,json,re,shutil,subprocess,sys

def finish(root,website,edition,config):
    stage=root/'output/document-download-staging'
    shutil.copyfile(website/'styles.css',stage/'styles.css')
    (stage/'assets').mkdir(exist_ok=True)
    shutil.copyfile(website/'assets/dej_software_footer.webp',stage/'assets/dej_software_footer.webp')
    (stage/'assets/js').mkdir(parents=True,exist_ok=True)
    for rel in ['assets/js/dej-community-links.js','assets/dej-affiliations.webp']:shutil.copyfile(website/rel,stage/rel)
    data=stage/'data-ark';data.mkdir(exist_ok=True)
    for name in ['collection-catalogue.pdf','feature-catalogue.pdf']:
        shutil.copyfile(root/'app/static'/name,data/name)
    output=root/'output/document-downloads'
    subprocess.run([sys.executable,str(root/'tools/package_document_downloads.py'),'--website',str(stage),'--output',str(output),'--edition',edition],check=True,stdout=subprocess.DEVNULL)
    record=json.loads((output/'download-manifest.json').read_text(encoding='utf-8'))
    previous=json.loads((root/config['download_history']).read_text(encoding='utf-8'))
    replaced={url:record['pdfs'][name] for name,url in previous['pdfs'].items()}
    # Only lightweight download landing pages are created in the public archive tree.
    for key,asset in record['editions'].items():
        folder=website/'data-ark/editions'/key;folder.mkdir(parents=True,exist_ok=True)
        text='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Archived Data Ark handbook | DEJ Software</title><link rel="stylesheet" href="/styles.css"></head><body><header class="wrap header ark-publication-header"><a class="header-brand" href="/" aria-label="DEJ Software home"><img src="/assets/dej_software_footer.webp" width="1024" height="192" alt="DEJ Software™"></a><p><a href="/#pharos">← Pharos Data Ark</a></p></header><main class="wrap collection-document"><h1>Archived Data Ark handbook</h1><p>Edition '+html.escape(key)+'</p><p><a class="button" href="'+html.escape(asset['url'],quote=True)+'">Download this handbook edition (ZIP)</a></p><p>Extract the entire ZIP and open index.html.</p><p><a href="/data-ark/docs/">Read the current complete handbook online</a></p></main><script src="/assets/js/dej-community-links.js?v=1"></script></body></html>'
        (folder/'index.html').write_text(text,encoding='utf-8')
    for page in website.rglob('*.html'):
        if '.git' in page.parts or 'saved' in page.parts:continue
        def link(match):
            url=match.group(1);name=url.split('?')[0].rsplit('/',1)[-1]
            if page==website/'index.html' and url.startswith('https://github.com/DavJenkins/pharos/releases/download/'):
                for kind in ['collection','feature']:
                    if re.fullmatch('data-ark-'+kind+'-catalogue-[0-9a-f]{12}\\.pdf',name):return 'href="'+record['pdfs'][kind+'-catalogue.pdf']+'"'
                if re.fullmatch(r'data-ark-handbook-.+\.zip',name):return 'href="'+record['editions'][edition]['url']+'"'
            if url in replaced:return 'href="'+html.escape(replaced[url],quote=True)+'"'
            if name=='data-ark-collection-catalogue.pdf':name='collection-catalogue.pdf'
            if name in record['pdfs']:return 'href="'+html.escape(record['pdfs'][name],quote=True)+'"'
            # Permanent edition links lead to that edition's download page.
            if url.startswith('/data-ark/editions/'):
                parts=url.split('/')
                if len(parts)>4 and parts[3] in record['editions']:return 'href="/data-ark/editions/'+parts[3]+'/"'
            return match.group(0)
        page.write_text(re.sub(r'href="([^"]+)"',link,page.read_text(encoding='utf-8-sig')),encoding='utf-8')
    (website/'data-ark/downloads.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
