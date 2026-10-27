#!/usr/bin/env python3
"""Install pinned public DEJ communication tools and register their offline launchers."""
import argparse,hashlib,json,shutil,sys
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
 atomic_write(root/'communication/index.html',page.encode())
 return config

def register(config,manifest_path=ROOT/'dataark.yaml'):
 import fcntl
 from tools.content_lock import acquire
 with Path('/var/lib/dataark/updates/worker.lock').open('a') as lock:
  acquire(lock);data=load_manifest(manifest_path)
  repo={'id':'communication-accessibility','category':'content_sources','title':'Communication & Accessibility','description':'Communicate browser speech tool and an offline Android installer for Communicate Keyboard. Speech requires an offline voice on the device you use.','collapse_assets':True,'artwork':{'path':'app/static/assets/icons/DEJ-hanging-sign.webp','alt':'DEJ Software hanging sign'},'update_policy':'manual','refresh_interval':'never','links':[{'title':'Open Communicate','url':'/library-files/communication/communicate/index.html'},{'title':'Android keyboard installer & setup','url':'/library-files/communication/index.html'}]}
  data['repositories']=[r for r in data['repositories'] if r['id']!=repo['id']]+[repo]
  ids=['communicate-web','communicate-keyboard-android']
  sources=[config['files'][0],config['files'][-1]]
  titles=['Communicate — offline browser communication tool','Communicate Keyboard — Android development build '+config['keyboard']['versionName']]
  for identifier,item,title in zip(ids,sources,titles):
   asset={'id':identifier,'repository_id':repo['id'],'category':'utilities_binaries','title':title,'relative_path':item['path'],'service_endpoint':'/library-files/'+item['path'],'download_url':item['url'],'expected_hash':item['sha256'],'update_policy':'manual','refresh_interval':'never','source_note':'Pinned public publisher files. Supporting web assets are restored by the communication recipe. Original DEJ Software notices retained.'}
   data['assets']=[a for a in data['assets'] if a['id']!=identifier]+[asset]
  atomic_write(manifest_path,serialize(data).encode())

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cache',type=Path);args=parser.parse_args()
 root=Path('/mnt/storage')
 if not root.is_mount():raise SystemExit('Content SSD must be mounted')
 config=install(root,args.cache);register(config);print('Verified and registered Communicate and Communicate Keyboard.')
if __name__=='__main__':main()
