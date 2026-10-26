#!/usr/bin/env python3
"""Vendor a pinned, integrity-checked Swagger UI for offline documentation."""
import base64
import hashlib
import io
import json
from pathlib import Path
import tarfile
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
VERSION = '5.34.0'
INTEGRITY = 'sha512-H6tAIjr3XqE31PbkZl0OFya1ziRLDfTwh3J6OHdumPtPCLfjTnyLeagl/55kFNZcTOz9a9QI9WP0FXldwiGJag=='
URL = 'https://registry.npmjs.org/swagger-ui-dist/-/swagger-ui-dist-' + VERSION + '.tgz'

def main():
    with urlopen(URL, timeout=60) as response: data = response.read(24 * 1024**2 + 1)
    if len(data) > 24 * 1024**2: raise ValueError('Swagger package exceeds size bound')
    if 'sha512-' + base64.b64encode(hashlib.sha512(data).digest()).decode() != INTEGRITY:
        raise ValueError('Swagger package integrity mismatch')
    target = ROOT / 'app/static/assets/vendor/swagger-ui'
    target.mkdir(parents=True, exist_ok=True)
    hashes = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as package:
        for name in ['swagger-ui-bundle.js', 'swagger-ui.css', 'favicon-32x32.png', 'LICENSE', 'NOTICE']:
            member = package.getmember('package/' + name)
            if not member.isfile(): raise ValueError('Expected regular package asset')
            content = package.extractfile(member).read()
            path = target / name
            path.write_bytes(content); path.chmod(0o644)
            hashes[name] = hashlib.sha256(content).hexdigest()
    (target / 'source.json').write_text(json.dumps({'package': 'swagger-ui-dist', 'version': VERSION,
        'url': URL, 'integrity': INTEGRITY, 'license': 'Apache-2.0', 'sha256': hashes}, indent=2) + '\n')
    print('Vendored Swagger UI', VERSION, 'for offline use')

if __name__ == '__main__': main()
