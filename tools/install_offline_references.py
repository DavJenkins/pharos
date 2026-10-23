#!/usr/bin/env python3
"""Fetch pinned viewer dependencies and official preparedness PDFs. Run explicitly as caretaker."""
import base64, hashlib, io, json, tarfile, urllib.request, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STATIC=ROOT/'app/static'
CONTENT=Path('/mnt/storage')
def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (DataArk offline library)'})
    with urllib.request.urlopen(req,timeout=90) as response: return response.read()
def put(path,data):
    path.parent.mkdir(parents=True,exist_ok=True); temp=path.with_suffix(path.suffix+'.part');temp.write_bytes(data);temp.replace(path);path.chmod(0o644)
def main():
    provenance=[]
    for package,version,wanted in [
        ('maplibre-gl','5.24.0',['dist/maplibre-gl.js','dist/maplibre-gl.css','LICENSE.txt']),
        ('pmtiles','4.5.0',['dist/pmtiles.js','LICENSE']),
        ('@protomaps/basemaps','5.7.2',['dist/basemaps.js','LICENSE'])]:
        metadata=json.loads(fetch('https://registry.npmjs.org/'+package+'/'+version));url=metadata['dist']['tarball'];data=fetch(url)
        alg,digest=metadata['dist']['integrity'].split('-',1)
        if base64.b64encode(hashlib.new(alg,data).digest()).decode()!=digest: raise ValueError('npm integrity mismatch')
        folder=STATIC/'assets/vendor/maps'/package.split('/')[-1]
        with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive:
            for name in wanted:
                candidates=[m for m in archive.getmembers() if m.isfile() and (m.name=='package/'+name or ('LICENSE' in name and 'license' in m.name.lower()))]
                if not candidates:
                    if 'LICENSE' in name:
                        put(folder/'LICENSE-NOTICE.txt',('Package license: '+str(metadata.get('license'))+'; source: '+str(metadata.get('repository'))+'\n').encode()); continue
                    raise ValueError('Missing package file '+name)
                for member in candidates: put(folder/Path(member.name).name,archive.extractfile(member).read())
        if package=='pmtiles':
            put(folder/'LICENSE',fetch('https://raw.githubusercontent.com/protomaps/PMTiles/main/LICENSE'))
        if package=='@protomaps/basemaps':
            for filename in ['LICENSE.md','LICENSE_DATA.md']:
                put(folder/filename,fetch('https://raw.githubusercontent.com/protomaps/basemaps/main/'+filename))
        provenance.append({'package':package,'version':version,'url':url,'integrity':metadata['dist']['integrity']})
        print('Vendored',package,version,flush=True)
    commit='028c18f713baecad011301ff7a69acc39bcc2ae7'
    url='https://github.com/protomaps/basemaps-assets/archive/'+commit+'.zip';data=fetch(url)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for name in archive.namelist():
            parts=name.split('/')[1:];relative='/'.join(parts)
            if name.endswith('/') or '..' in parts: continue
            if relative.startswith('fonts/') or relative.startswith('sprites/v4/light') or relative in ('README.md','LICENSE'):
                put(STATIC/'assets/vendor/maps/protomaps-assets'/relative,archive.read(name))
    provenance.append({'repository':'protomaps/basemaps-assets','commit':commit,'url':url,'sha256':hashlib.sha256(data).hexdigest()})
    put(STATIC/'assets/vendor/maps/provenance.json',(json.dumps(provenance,indent=2)+'\n').encode())
    docs=[
      ('fema-ready.pdf','FEMA / Ready.gov — Are You Ready?','2021 hosted edition','https://www.ready.gov/sites/default/files/2021-11/are-you-ready-guide.pdf'),
      ('cert-participant-2019.pdf','FEMA CERT Basic Training Participant Manual','2019','https://www.ready.gov/sites/default/files/2019.CERT_.Basic_.PM_FINAL_508c.pdf'),
      ('cert-hazards-2019.pdf','FEMA CERT Hazard Annexes','2019','https://www.ready.gov/sites/default/files/2019.CERT_.HazardAnnexes.PM_.FINAL_.508c.pdf'),
      ('cert-all-abilities.pdf','FEMA CERT Annex for All Abilities','2015','https://www.fema.gov/sites/default/files/2020-07/fema_cert-annex-for-all-abilities_091615.pdf'),
      ('mema-flyer.pdf','Massachusetts MEMA Emergency Preparedness Flyer','edition not specified','https://www.mass.gov/doc/english-emergency-preparedness-flyer/download'),
      ('mema-winter-2026.pdf','Massachusetts MEMA Winter Weather Preparedness Toolkit','2026','https://www.mass.gov/doc/winter-weather-preparedness-toolkit-2026/download')]
    records=[]
    from datetime import datetime,timezone
    for filename,title,edition,url in docs:
        record=dict(filename=filename,title=title,edition=edition,source=url,retrieved=datetime.now(timezone.utc).isoformat())
        try:
            data=fetch(url)
            if not data.startswith(b'%PDF-'): raise ValueError('Not a PDF')
            put(CONTENT/'preparedness'/filename,data);record.update(status='installed',bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
            print('Installed',filename,len(data),flush=True)
        except Exception as e: record.update(status='unavailable',error=str(e));print('Unavailable',filename,str(e),flush=True)
        records.append(record)
    put(CONTENT/'preparedness/sources.json',(json.dumps(records,indent=2)+'\n').encode())
if __name__=='__main__': main()
