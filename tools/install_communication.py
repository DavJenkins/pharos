#!/usr/bin/env python3
"""Install pinned public DEJ communication tools and register their offline launchers."""
import argparse,hashlib,html,json,shutil,sys
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.content_profile import download,inside
from app.services.manifest import load_manifest,atomic_write
from tools.library_removal import serialize
CATALOGUE=ROOT/'deploy/reference/communication.json'

def verify(path,item):
 return path.is_file() and not path.is_symlink() and path.stat().st_size==item['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']

def install(root,cache=None):
 config=json.loads(CATALOGUE.read_text(encoding='utf-8'))
 for item in config['files']:
  target=inside(root,item['path'])
  cached=inside(cache,item['path']) if cache else None
  if verify(target,item):continue
  if cached and verify(cached,item):atomic_write(target,cached.read_bytes())
  else:download(item,root,{'reserve_gib':10,'download_rate_kib':0},verify_existing=True)
  if not verify(target,item):raise ValueError('Communication file verification failed: '+item['path'])
 record={**config,'installed_at':datetime.now(timezone.utc).isoformat()}
 atomic_write(root/'communication/sources.json',(json.dumps(record,indent=2)+'\n').encode())
 apk=config['keyboard']['apk'];version=config['keyboard']['versionName'];sha=config['keyboard']['sha256']
 page="""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Communication &amp; Accessibility — Data Ark</title><link rel="stylesheet" href="/assets/css/ark-pages.css"></head><body><main class="ark-page"><a class="ark-page-brand" href="/">Data Ark</a><h1>Communication &amp; Accessibility</h1><p>Tools for people who find speech or precise touchscreen typing difficult. These copies are served locally by the Ark.</p><section><h2>Communicate</h2><p>Compose a message with a forgiving dwell keyboard, saved phrases and text-to-speech.</p><p><a class="button" href="communicate/index.html">Open Communicate</a></p><p>Works while connected to the Ark without upstream internet. Speech comes from the device you are using: install an offline voice in its speech settings beforehand. A voice requiring internet will not work during an outage.</p><p>Messages, preferences and saved phrases stay in the browser on that device. Different Ark names/IP addresses are separate browser origins and can have separate saved settings. Over plain HTTP, browsers may not allow installation or caching for use after disconnecting from the Ark; the local page itself remains available while connected.</p></section><section><h2>Communicate Keyboard for Android</h2><p><strong>Development build VERSION</strong> — an Android input-method keyboard for text fields in other apps. Requires Android 8.0 or newer.</p><p><a class="button" href="android/APK" download>Download Android installer (1.6 MB)</a></p><p>Download on the Android device, open the APK and allow installation from that browser if Android asks. Then open Communicate Keyboard, choose Enable keyboard, and select it as your input method. Install an offline text-to-speech voice for speech without internet.</p><p>This development build uses a different signing identity from Google Play builds and cannot update an existing Play installation in place. Keep your saved settings and phrases before changing installations. This page does not install anything on your device automatically.</p><details><summary>Integrity and source</summary><p>SHA-256: <code style="overflow-wrap:anywhere">SHA</code></p><p><a href="sources.json">Pinned source URLs, sizes, hashes and version details</a>. <a href="https://dejsoftware.com/communicate-keyboard-dev/">Publisher (internet required)</a>.</p></details></section><p><a href="/docs/20-Administration/CommunicationTools.html">Offline use and maintenance</a> · <a href="/">Return to the library</a></p></main></body></html>"""
 page=page.replace('VERSION',version).replace('android/APK','android/'+apk).replace('SHA</code>',sha+'</code>')
 if config.get('bootstrap'):
  kit=config['bootstrap'];package=next(f for f in config['files'] if f['path']==kit['path'])
  relative=Path(package['path']).relative_to('communication').as_posix()
  checksums=Path(package['path']).parent/'SHA256SUMS'
  metadata=Path(package['path']).parent/'release.json'
  atomic_write(inside(root,checksums.as_posix()),(package['sha256']+'  '+Path(package['path']).name+'\n').encode())
  atomic_write(inside(root,metadata.as_posix()),(json.dumps(kit,indent=2)+'\n').encode())
  section='<section id="bootstrap"><h2>Build another Data Ark</h2><p>Public bootstrap kit '+html.escape(kit['version'])+' ('+format(package['bytes']/1024**2,'.1f')+' MiB). Download this local copy while connected to the Ark; no upstream internet is needed for the download.</p><p><a class="button" href="'+html.escape(relative,quote=True)+'" download>Download Ark bootstrap kit</a></p><p>Extract it onto a prepared content drive and follow its README. It contains public configuration and software, without library payloads, passwords or device identities. Setting up a new Pi still requires internet for system and software dependencies; content restoration is chosen separately.</p><p><a href="/docs/30-Developer/StockPiSetup.html">Installation guide</a> · <a href="/clone.html">Clone directly to a mounted drive</a></p><details><summary>Version, integrity and source</summary><p>SHA-256: <code style="overflow-wrap:anywhere">'+package['sha256']+'</code></p><p><a href="'+checksums.relative_to('communication').as_posix()+'">Checksum file</a> · <a href="'+metadata.relative_to('communication').as_posix()+'">Release details</a></p><p>The normal publisher checks watch the release notice. New releases are reviewed and pinned before replacing this package.</p></details></section>'
  page=page.replace('<p><a href="/docs/20-Administration/CommunicationTools.html">',section+'<p><a href="/docs/20-Administration/CommunicationTools.html">')
  page=page.replace('Communication &amp; Accessibility','DEJ Software').replace('Tools for people who find speech or precise touchscreen typing difficult. These copies are served locally by the Ark.','Communication tools and the Data Ark bootstrap kit, preserved and served locally by the Ark.')
 atomic_write(root/'communication/index.html',page.encode())
 return config

def register(config,manifest_path=ROOT/'dataark.yaml'):
 import fcntl
 from tools.content_lock import acquire
 with Path('/var/lib/dataark/updates/worker.lock').open('a') as lock:
  acquire(lock);data=load_manifest(manifest_path)
  repo=config.get('repository') or {'id':'communication-accessibility','category':'content_sources','title':'Communication & Accessibility','description':'Communicate browser speech tool and an offline Android installer for Communicate Keyboard. Speech requires an offline voice on the device you use.','collapse_assets':True,'artwork':{'path':'app/static/assets/icons/DEJ-hanging-sign.webp','alt':'DEJ Software hanging sign'},'update_policy':'manual','refresh_interval':'never','links':[{'title':'Open Communicate','url':'/library-files/communication/communicate/index.html'},{'title':'Android keyboard installer & setup','url':'/library-files/communication/index.html'}]}
  data['repositories']=[r for r in data['repositories'] if r['id']!=repo['id']]+[repo]
  ids=['communicate-web','communicate-keyboard-android']
  sources=[next(f for f in config['files'] if f['path']=='communication/communicate/index.html'),next(f for f in config['files'] if f['path']=='communication/android/'+config['keyboard']['apk'])]
  titles=['Communicate — offline browser communication tool','Communicate Keyboard — Android development build '+config['keyboard']['versionName']]
  entries=config.get('assets')
  if entries is None:
   entries=[]
   for identifier,item,title in zip(ids,sources,titles):
    entries.append({'id':identifier,'repository_id':repo['id'],'category':'utilities_binaries','title':title,'relative_path':item['path'],'service_endpoint':'/library-files/'+item['path'],'download_url':item['url'],'expected_hash':item['sha256'],'update_policy':'manual','refresh_interval':'never','source_note':'Pinned public publisher files. Supporting web assets are restored by the communication recipe. Original DEJ Software notices retained.'})
  previous={a['id']:a for a in data['assets']}
  changed=[a for a in entries if a['id'] not in previous or previous[a['id']].get('removed') or any(previous[a['id']].get(k)!=v for k,v in a.items())]
  for asset in entries:
   if asset['repository_id']!=repo['id']:raise ValueError('Configured software asset belongs to another collection')
   data['assets']=[a for a in data['assets'] if a['id']!=asset['id']]+[asset]
  atomic_write(manifest_path,serialize(data).encode())
  return changed

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cache',type=Path);args=parser.parse_args()
 root=Path('/mnt/storage')
 if not root.is_mount():raise SystemExit('Content SSD must be mounted')
 config=install(root,args.cache);changed=register(config)
 from app.services.collection_changes import safe_record
 for asset in changed:safe_record('installed',collection_id=asset['id'],title=asset['title'],action='install')
 print('Verified and registered the DEJ Software collection.')
if __name__=='__main__':main()
