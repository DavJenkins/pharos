#!/usr/bin/env python3
"""Vendor the pinned official Mozilla PDF.js distribution for offline use."""
import base64,hashlib,io,json,tarfile,urllib.request
from pathlib import Path
VERSION='6.4.299'
URL='https://registry.npmjs.org/pdfjs-dist/-/pdfjs-dist-'+VERSION+'.tgz'
INTEGRITY='sha512-AVl138zALtfaAPvADulE0PZThbYzCBS79nL4pOSL/6Sm/4AH5A21BD9VHt97OlCuzJuCpmeZtAtkinisF4Vb1g=='
ROOT=Path(__file__).resolve().parents[1]
def main():
 with urllib.request.urlopen(URL,timeout=90) as r:data=r.read(100*1024**2+1)
 if len(data)>100*1024**2:raise SystemExit('Archive size exceeded limit')
 if 'sha512-'+base64.b64encode(hashlib.sha512(data).digest()).decode()!=INTEGRITY:raise SystemExit('Publisher integrity mismatch')
 dest=ROOT/'app/static/assets/vendor/pdfjs';dest.mkdir(parents=True,exist_ok=True)
 with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as tar:
  for member in tar:
   parts=Path(member.name).parts
   if len(parts)<2 or parts[0]!='package' or '..' in parts or not member.isfile():continue
   rel=Path(*parts[1:]);name=rel.as_posix()
   if name not in ['build/pdf.mjs','build/pdf.worker.mjs','LICENSE'] and parts[1] not in ['cmaps','standard_fonts','wasm']:continue
   path=dest/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(tar.extractfile(member).read());path.chmod(0o644)
 (dest/'source.json').write_text(json.dumps({'product':'Mozilla PDF.js','version':VERSION,'url':URL,'integrity':INTEGRITY,'license':'Apache-2.0','documentation':'https://mozilla.github.io/pdf.js/getting_started/'},indent=2)+'\n')
 print('Installed PDF.js',VERSION,flush=True)
if __name__=='__main__':main()
