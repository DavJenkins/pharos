#!/usr/bin/env python3
"""Install pinned, integrity-checked PDF editing dependencies from their official npm packages."""
import base64,hashlib,io,json,shutil,tarfile,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'app/static/assets/vendor/pdf-lib'
PACKAGES=[('pdf-lib','1.17.1','https://registry.npmjs.org/pdf-lib/-/pdf-lib-1.17.1.tgz','sha512-V/mpyJAoTsN4cnP31vc0wfNA1+p20evqqnap0KLoRUN0Yk/p3wN52DOEsL4oBFcLdb76hlpKPtzJIgo67j/XLw==',{'dist/pdf-lib.min.js':'pdf-lib.min.js','LICENSE.md':'LICENSE-pdf-lib.md'}),('@pdf-lib/fontkit','1.1.1','https://registry.npmjs.org/@pdf-lib/fontkit/-/fontkit-1.1.1.tgz','sha512-KjMd7grNapIWS/Dm0gvfHEilSyAmeLvrEGVcqLGi0VYebuqqzTbgF29efCx7tvx+IEbG3zQciRSWl3GkUSvjZg==',{'dist/fontkit.umd.min.js':'fontkit.umd.min.js','README.md':'README-fontkit.md','package.json':'package-fontkit.json'})]
def main():
 DEST.mkdir(parents=True,exist_ok=True)
 for name,version,url,integrity,files in PACKAGES:
  with urllib.request.urlopen(url,timeout=60) as r:data=r.read(40*1024**2+1)
  if len(data)>40*1024**2 or 'sha512-'+base64.b64encode(hashlib.sha512(data).digest()).decode()!=integrity:raise SystemExit('Package integrity mismatch: '+name)
  with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as tar:
   for source,target in files.items():
    member=tar.getmember('package/'+source)
    if not member.isfile():raise SystemExit('Invalid package entry')
    p=DEST/target;p.write_bytes(tar.extractfile(member).read());p.chmod(0o644)
 shutil.copyfile('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',DEST/'DejaVuSans.ttf');shutil.copyfile('/usr/share/doc/fonts-dejavu-core/copyright',DEST/'LICENSE-DejaVu.txt')
 (DEST/'source.json').write_text(json.dumps({'packages':[{'name':n,'version':v,'url':u,'integrity':i} for n,v,u,i,_ in PACKAGES],'font':'Debian fonts-dejavu-core / DejaVuSans.ttf','font_sha256':hashlib.sha256((DEST/'DejaVuSans.ttf').read_bytes()).hexdigest()},indent=2)+'\n')
 print('Offline PDF editing dependencies installed.')
if __name__=='__main__':main()
