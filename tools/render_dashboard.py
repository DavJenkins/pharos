#!/usr/bin/env python3
"""Render the landing page from the Data Ark v1.4 manifest."""
import argparse
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.manifest import build, ManifestError, version_dashboard_assets

def version_static_pages(static):
    for page in Path(static).rglob('*.html'):
        if page.is_symlink():
            continue
        original=page.read_text(encoding='utf-8')
        updated=version_dashboard_assets(original,static)
        if updated!=original:
            page.write_text(updated,encoding='utf-8')


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
    if args.output.resolve() == (ROOT/'app/static/index.html').resolve():
        version_static_pages(ROOT/'app/static')
    print(f'Rendered {len(result.get("repositories", []))} configured repositories.')
    print('No content downloads or updates were started.')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
