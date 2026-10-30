#!/usr/bin/env python3
"""Render the landing page from the Data Ark v1.4 manifest."""
import argparse
import html
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.manifest import build, ManifestError, version_dashboard_assets
from app.services.system import installed_ram

def version_static_pages(static):
    for page in Path(static).rglob('*.html'):
        if page.is_symlink():
            continue
        original=page.read_text(encoding='utf-8')
        updated=version_dashboard_assets(original,static)
        if updated!=original:
            page.write_text(updated,encoding='utf-8')


def raspberry_pi_hardware(model_paths=(Path('/proc/device-tree/model'),Path('/sys/firmware/devicetree/base/model'))):
    """Show vendor credit only when the machine reports Raspberry Pi hardware."""
    for path in model_paths:
        try:
            if path.read_bytes().rstrip(b'\0').decode('utf-8',errors='replace').strip().startswith('Raspberry Pi '):
                return True
        except OSError:
            continue
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', nargs='?', type=Path, default=ROOT / 'dataark.yaml')
    parser.add_argument('output', nargs='?', type=Path, default=ROOT / 'app/static/index.html')
    parser.add_argument('--content-root', type=Path)
    parser.add_argument('--refresh-artwork', action='store_true')
    args = parser.parse_args()
    try:
        result = build(args.manifest, ROOT / 'app/templates/index.html', args.output, content_root=args.content_root, refresh_artwork=args.refresh_artwork)
    except (ManifestError, OSError) as error:
        print(f'Manifest build failed: {error}', file=sys.stderr)
        return 1
    page=args.output.read_text(encoding="utf-8")
    if raspberry_pi_hardware():page=page.replace('<footer class="platform-credit" hidden>','<footer class="platform-credit">')
    args.output.write_text(page,encoding="utf-8")
    capacity=installed_ram()
    if capacity:
        page=args.output.read_text(encoding='utf-8')
        args.output.write_text(page.replace('<body', '<body data-installed-ram="'+html.escape(capacity,quote=True)+'"',1),encoding='utf-8')
    if args.output.resolve() == (ROOT/'app/static/index.html').resolve():
        version_static_pages(ROOT/'app/static')
    print(f'Rendered {len(result.get("repositories", []))} configured repositories.')
    print('No content downloads or updates were started.')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
