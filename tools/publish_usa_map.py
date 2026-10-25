#!/usr/bin/env python3
"""Publish only a verified national map, retaining the previous working archive."""
from pathlib import Path
import fcntl,hashlib,json,os,shutil,subprocess,time
import yaml
ROOT=Path(__file__).resolve().parents[1]
STATE=Path('/var/lib/dataark/maps/usa-expansion.json')
STAGE=Path('/mnt/storage/maps/osm/usa.staging.pmtiles')
TARGET=STAGE.with_name('usa.pmtiles')
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(4*1024**2),b''):h.update(chunk)
    return h.hexdigest()
def git(*args):subprocess.run(['runuser','-u','admin','--','git','-C',str(ROOT),*args],check=True)
def publish():
    record=json.loads(STATE.read_text())
    if record['state'] not in ('verified','publishing'):raise RuntimeError('The national archive has not been verified.')
    if record.get('file')!=str(STAGE):raise RuntimeError('Unexpected staging path.')
    candidate=STAGE if STAGE.is_file() else TARGET
    if candidate.is_symlink() or digest(candidate)!=record['sha256']:raise RuntimeError('The verified map checksum no longer matches.')
    if record['header'].get('maxzoom')!=15:raise RuntimeError('Unexpected map zoom detail.')
    record['state']='publishing';STATE.write_text(json.dumps(record,indent=2)+'\n')
    with Path('/var/lib/dataark/maps/worker.lock').open('a') as lock,Path('/var/lib/dataark/updates/worker.lock').open('a') as updates:
        fcntl.flock(lock,fcntl.LOCK_EX);fcntl.flock(updates,fcntl.LOCK_EX)
        metadata=json.loads((ROOT/'deploy/reference/osm-usa.json').read_text())
        metadata.update(path='maps/osm/usa.pmtiles',sha256=record['sha256'],bytes=record['bytes'],configuration_state='verified and published')
        if STAGE.exists():os.replace(STAGE,TARGET)
        source=TARGET.parent/'source.json'
        if source.exists() and not (TARGET.parent/'massachusetts-source.json').exists():shutil.copy2(source,TARGET.parent/'massachusetts-source.json')
        source.write_text(json.dumps(metadata,indent=2)+'\n')
        for name in ['osm-usa.json','osm-massachusetts.json']:(ROOT/'deploy/reference'/name).write_text(json.dumps(metadata,indent=2)+'\n')
        p=ROOT/'dataark.yaml';manifest=yaml.safe_load(p.read_text())
        for repo in manifest['repositories']:
            if repo['id']=='openstreetmap':repo['description']='All 50 U.S. states, including Alaska, the Aleutians and Hawaii, plus adjoining areas. Offline street map with local pan and zoom; no search or routing.'
        for asset in manifest['assets']:
            if asset['id']=='osm-massachusetts':
                asset.update(title='All 50 U.S. states offline street map (October 22, 2026)',relative_path='maps/osm/usa.pmtiles',expected_hash=record['sha256'],source_note='Rectangular extracts cover the contiguous 48 states, Alaska/Aleutians and Hawaii/Northwestern Hawaiian Islands, with adjoining areas. Native zoom 0–15. OSM ODbL, Protomaps and Natural Earth attribution. Manual updates.')
        p.write_text(yaml.safe_dump(manifest,sort_keys=False,allow_unicode=True))
        p=ROOT/'app/static/assets/js/offline-map.js';s=p.read_text().replace('center:[-71.80,42.35],zoom:8','center:[-96,38],zoom:3.5').replace('maxBounds:[[-73.51,41.23],[-69.90,42.89]],',"bounds:[[-125,24],[-66,50]],fitBoundsOptions:{padding:24},").replace('/library-files/maps/osm/massachusetts.pmtiles','/library-files/maps/osm/usa.pmtiles')
        marker="    map.addControl(new maplibregl.NavigationControl());"
        controls="""    const regions={conus:[[-125,24],[-66,50]],alaska:[[-188,51],[-129,72]],hawaii:[[-179,18],[-154,29]]};
    for(const button of document.querySelectorAll('[data-map-region]'))button.addEventListener('click',()=>{map.fitBounds(regions[button.dataset.mapRegion],{padding:24,duration:500});});
"""
        if 'const regions=' not in s:s=s.replace(marker,controls+marker)
        p.write_text(s)
        p=ROOT/'app/static/maps.html';s=p.read_text().replace('Massachusetts and adjoining border areas','All 50 U.S. states, plus adjoining areas').replace('/library-files/maps/osm/massachusetts.pmtiles','/library-files/maps/osm/usa.pmtiles')
        if 'data-map-region' not in s:s=s.replace('<p id="message"','<p class="map-regions" aria-label="Map region"><button type="button" data-map-region="conus">Lower 48</button> <button type="button" data-map-region="alaska">Alaska</button> <button type="button" data-map-region="hawaii">Hawaii</button></p><p id="message"')
        s=s.replace('</style>','body{height:100dvh;display:flex;flex-direction:column}header{flex:none}#map{height:auto;flex:1;min-height:280px}.map-regions button{font:inherit;font-size:.85rem;padding:.35rem .7rem;min-height:36px;border:1px solid #af9145;border-radius:6px;background:#f5df9b;color:#203e54;cursor:pointer}.map-regions button:focus-visible{outline:3px solid white;outline-offset:2px}</style>') if '.map-regions button' not in s else s
        p.write_text(s)
        p=ROOT/'app/static/library.html';s=p.read_text().replace('The Ark’s offline street map covers Massachusetts and adjoining border areas.','The Ark’s offline street map covers all 50 U.S. states, including Alaska, the Aleutians, Hawaii and the Northwestern Hawaiian Islands, plus adjoining areas.').replace('Coverage is regional, not worldwide.','Coverage is nationwide, not worldwide.');p.write_text(s)
        p=ROOT/'docs/20-Administration/OfflineReferences.md';s=p.read_text();start=s.index('## Massachusetts street map');end=s.index('## Preparedness and CERT');s=s[:start]+"""## All 50 U.S. states street map
Open `/maps.html`. Map data, scripts, styles, glyphs and sprites are all local. The viewer initially shows the lower 48; Lower 48 / Alaska / Hawaii buttons reposition the view. Alaska includes the Aleutians and Hawaii includes the Northwestern Hawaiian Islands. Rectangular cutouts include neighboring areas; U.S. territories are not a promised coverage set. WebGL is required. Pan, zoom and scale are available; search and route planning are not implemented.

The active archive is `/mnt/storage/maps/osm/usa.pmtiles`, exposed at `/library-files/maps/osm/usa.pmtiles`. Native zooms are 0–15; higher viewer zooms enlarge existing detail. Source: Protomaps build 22 October 2026. Coverage geometry and source/checksum are in `deploy/reference/osm-usa.geojson`, `osm-usa.json`, and the drive's `maps/osm/source.json`. The earlier Massachusetts file and `massachusetts-source.json` remain for rollback; the old download link refers to that older regional copy. Existing flood, parcel and topographic datasets remain Massachusetts-focused and separate.

Attribution: OpenStreetMap contributors (ODbL), Protomaps Produced Work and Natural Earth. Preserve attribution when copying. See https://www.openstreetmap.org/copyright and https://docs.protomaps.com/basemaps/downloads . Software and font license notices are retained with the local viewer dependencies.

### Reconstruction and updates
The street basemap remains manually updated, independent of monthly GIS and Kiwix workers. `tools/content_profile.py restore --only osm --apply` reconstructs the selected national archive from the public source recipe, verifies it, checks the recorded hash and publishes atomically. The regional source cutout is downloaded, not the entire planet. The content profile and its geometry travel in DATA-ARK-CONFIG and the recovery kit. Source availability is required. For a different build, review the source edition, checksum and viewer date together.

"""+s[end:]
        s+='\nPublished national map SHA-256: `'+record['sha256']+'`; '+str(record['bytes'])+' bytes. Verified before replacing the active viewer target.\n';p.write_text(s)
        subprocess.run(['/usr/bin/python3','tools/content_profile.py','export'],cwd=ROOT,check=True)
        subprocess.run([str(ROOT/'venv/bin/python'),'-m','unittest','tests.test_manifest','tests.test_maps','tests.test_content_profile'],cwd=ROOT,check=True)
        files=['deploy/reference/osm-usa.json','deploy/reference/osm-massachusetts.json','app/static/assets/js/offline-map.js','app/static/maps.html','app/static/library.html','docs/20-Administration/OfflineReferences.md','config/content/content.yaml','config/content/content-lock.json','config/content/public-manifest.yaml']
        for name in files:os.chown(ROOT/name,1000,1000)
        git('add','--',*files)
        for name in files:
            old=subprocess.check_output(['git','-c','safe.directory='+str(ROOT),'-C',str(ROOT),'ls-tree','HEAD',name],text=True).split();mode=old[0] if old else '100644';git('update-index','--chmod='+('+' if mode=='100755' else '-')+'x','--',name)
        git('diff','--cached','--check');git('commit','-m','Publish verified offline street map for all 50 U.S. states')
        subprocess.run(['bash','deploy/deploy-web.sh'],cwd=ROOT,check=True)
        subprocess.run(['/usr/bin/python3','tools/prepare_recovery.py'],cwd=ROOT,check=True)
        git('bundle','create','/var/lib/dataark/maps/usa-map-published.bundle','feature/readme-foundation')
        # Confirm the public viewer and byte-range archive endpoint before reporting ready.
        from urllib.request import Request,urlopen
        with urlopen('http://127.0.0.1/maps.html',timeout=20) as response:
            viewer=response.read().decode()
            if '/library-files/maps/osm/usa.pmtiles' not in viewer or 'data-map-region="alaska"' not in viewer:raise RuntimeError('The national viewer did not deploy correctly.')
        with urlopen(Request('http://127.0.0.1/library-files/maps/osm/usa.pmtiles',headers={'Range':'bytes=0-126'}),timeout=20) as response:
            if response.status!=206 or response.read(128)[:8]!=b'PMTiles\x03':raise RuntimeError('The published map byte-range endpoint failed verification.')
        record['state']='published';STATE.write_text(json.dumps(record,indent=2)+'\n')
def main():
    deadline=time.monotonic()+48*3600
    while time.monotonic()<deadline:
        record=json.loads(STATE.read_text()) if STATE.exists() else {}
        if record.get('state')=='published':return
        if record.get('state') in ('verified','publishing'):publish();return
        if record.get('state')=='failed':raise SystemExit('Extraction failed; existing map retained: '+record.get('error',''))
        time.sleep(20)
    raise SystemExit('Timed out waiting for extraction; existing map retained.')
if __name__=='__main__':main()
