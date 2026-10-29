#!/usr/bin/env python3
"""Generate the user-facing content guide from the same composition as the dashboard."""
from collections import defaultdict
from pathlib import Path
import sys
import re
from urllib.parse import quote
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.manifest import load_manifest
from app.services.dashboard_cards import compose

TOOLS = {
 'learning-home': [('Learning at home', '/learning.html', 'Separate levels for early learners, elementary, middle/high school and adults; reading, art/music, practical learning and a daily-learning outline. The curriculum shelf identifies installed teaching units and textbooks, with coverage and gaps by grade and subject.')],
 'games-activities': [('Activities', '/activities.html', 'PDF coloring and drawing, memory pairs, tic-tac-toe, sliding puzzle, word hunt, and ideas for play away from a screen.'), ('PDF coloring studio', '/coloring.html', 'Open a PDF, select a page, color or draw and save the result.'), ('Paper studio', '/printables.html', 'Printable paper patterns, ready-made packs and everyday worksheets; A4 and US Letter. Available patterns: Square grid; Engineering grid (5 subdivisions); Dot grid; Cross grid; Isometric / triangular; Isometric dots; Hexagonal; Polar coordinates; Logarithmic (both axes); Semi-logarithmic; Ruled lines; Wide ruled (8.7 mm); Narrow ruled (6.35 mm); Handwriting guides; Double-line handwriting; Cornell lined notes; Cornell grid notes; Cornell dot notes; Music staves; Guitar tablature; Bass tablature; Calligraphy guides; Character-writing squares; Chess / checkers board; Go board (19 × 19); Undated monthly calendar; Story & drawing page; Blank page.')],
 'forms-household': [('PDF form tool', '/pdf-forms.html', 'Open PDFs, fill interactive fields, write on the page, preview and save.'), ('Paper studio', '/printables.html', 'Emergency contacts, household/supply inventories, medication records, evacuation planning, pet care, expenses, receipts, maintenance logs, equipment handovers and project planning; printable in A4 and US Letter.')],
 'power-energy': [('Power planner', '/power.html', 'Load inventory, daily energy, battery/solar estimates and micro-hydro estimate; printable results.')],
 'radio-communications': [('Radio question drills', '/radio-study.html', 'Technician, General and Amateur Extra question pools with practice and round results.'), ('Offline callsign search', '/callsigns.html', 'FCC amateur licensee search, grid-square proximity, distance and bearing; snapshot/download information.')],
}
NOTES = {
 'wikipedia': 'A searchable archive, not a live Wikipedia connection. Individual articles are browsed inside Kiwix.',
 'project-gutenberg': 'Search and browse the English-language book archive in Kiwix. Individual titles are indexed inside the archive rather than repeated here. Book notices and jurisdiction-specific copyright status still apply.',
 'wikimed': 'The medical encyclopedia remains distinct from the First Aid & Caregiving collection; that card links here too.',
 'maps-navigation': 'The street maps are not nautical charts or a routing service. The expandable list below identifies the major Caribbean island groups.',
 'laws-codes': 'The state/territory collection is constitutional text (and the DC Home Rule Act/Charter), not a complete collection of every state statute, regulation or adopted building code. Massachusetts and local references have the narrower scope named in each title.',
 'repairs-maintenance': 'iFixit, practical repairs and the two vehicle collections stay distinct within this card. Honda owner manuals and quick guides are not factory workshop/service manuals.',
}
GAPS = {
 'forms-household': ['SSA SS-5 application for a Social Security card (blocked download).'],
 'food-cooking': ['Good and Cheap by Leanne Brown (blocked download).'],
 'wilderness-field': ['Forest Service Know Before You Go and Outdoor Safety (recorded URLs return 404).'],
 'power-energy': ['DOE Microhydropower Systems and Colorado Small Hydropower Handbook (recorded URLs return 404); the separate NCAT micro-hydro guide is installed.'],
 'preparedness': ['CERT Annex for All Abilities, MEMA Emergency Preparedness Flyer and MEMA Winter Weather Preparedness Toolkit (blocked downloads).'],
 'laws-codes': ['Massachusetts building-code preamble/contents, code adoption/source pages and small-claims rules source index (blocked downloads).', 'Full Gardner City Code text (dynamic source extraction unresolved); the official city source page is preserved.'],
}
ISLANDS = [
 'Greater Antilles: Cuba, Hispaniola (Haiti and the Dominican Republic), Jamaica and Puerto Rico.',
 'Virgin Islands: U.S. Virgin Islands and British Virgin Islands.',
 'Northern/eastern Lesser Antilles: Anguilla, Sint Maarten / Saint Martin, Saint Barthelemy, Antigua and Barbuda, Saint Kitts and Nevis, Montserrat and Guadeloupe.',
 'Southern Lesser Antilles: Dominica, Martinique, Saint Lucia, Barbados, Saint Vincent and the Grenadines, Grenada, Trinidad and Tobago.',
 'Southern Caribbean: Aruba, Bonaire and Curacao.',
 'Other island groups: Bahamas, Turks and Caicos, Cayman Islands.',
]

def generate(data, root):
    rows = defaultdict(list)
    for asset in data['assets']:
        if not asset.get('removed'):
            rows[asset['repository_id']].append({**asset, 'available': (root / asset['relative_path']).exists()})
    cards, rows = compose(data, rows)
    cards = [c for c in cards if c.get('enabled', True) and not (data['system'].get('hide_missing') and rows.get(c['id']) and not any(a['available'] for a in rows[c['id']]))]
    ids = [a['id'] for c in cards for a in rows.get(c['id'], [])]
    assert len(ids) == len(set(ids)), 'Duplicate content assignment'
    out = ['# Content sources: the landing-page collections', '',
        'This guide follows the same order and grouping as the landing page: ' + str(len(cards)) + ' content cards and ' + str(len(ids)) + ' registered content items. Archives, datasets and grouped packs count as items; their internal articles, books, map features and individual pages are not separate cards.', '',
        'Local links open saved content or browser tools on the Ark. Publisher links identify the original sources and require upstream internet. Saved editions are snapshots; a blocked publisher check does not mean the installed copy is missing. Long inventories expand below. Outstanding gaps are listed separately from installed material.', '',
        'Generated from `dataark.yaml` and the dashboard card composition by `tools/document_content_sources.py` whenever the web site is deployed. See [Manage Library](/library.html) for current installation and update state.', '', '## Card index', '']
    for number, card in enumerate(cards, 1):
        label = str(number) + '. ' + card['title']
        anchor = re.sub(r'[^a-z0-9]+', '-', label.lower()).strip('-')
        count = len(rows.get(card['id'], []))
        out.append('- [' + label + '](#' + anchor + ') — ' + str(count) + (' registered item' if count == 1 else ' registered items'))
    for number, card in enumerate(cards, 1):
        identifier = card['id']; items = rows.get(identifier, [])
        out += ['', '## ' + str(number) + '. ' + card['title'], '', card.get('description', ''), '', NOTES.get(identifier, ''), '', '### Open this collection', '']
        links = card.get('links', []) + [link for group in card.get('link_groups', []) for link in group['links']]
        for link in links:
            target = ('http://dataark:' + str(data['system'].get('services', {}).get('kiwix_port', 8080)) + link.get('path', '/')) if link.get('service') == 'kiwix' else link['url']
            out.append('- [' + link['title'] + '](' + target + ')' + (' (publisher; online)' if link.get('requires_internet') else ''))
        if identifier in TOOLS:
            out += ['', '### Included tools and activities', '']
            for title, target, detail in TOOLS[identifier]:out.append('- [' + title + '](' + target + ') — ' + detail)
        if identifier == 'maps-navigation':
            out += ['', '::: details All 50 U.S. states', '', 'The nationwide street-map archive covers all 50 states, including Alaska and Hawaii. This is one map dataset, not 50 separate downloads. ', '', ':::', '', '::: details Caribbean island groups and destinations', '', 'The configured rectangular extraction spans longitude -89 to -58 and latitude 9 to 28, to zoom 15. It includes the following major island groups and adjoining coasts; this is a coverage overview, not an enumeration of every small island or a guarantee of feature completeness.', '']
            out += ['- ' + island for island in ISLANDS]
            out += ['', 'Bermuda is outside this extraction. The map viewer offers quick locations for Sint Maarten, USVI/BVI, Puerto Rico and the Bahamas.', '', ':::']
        groups = []
        if identifier == 'laws-codes':
            groups = [('United States Code — titles and appendices', [a for a in items if a['id'].startswith('ref-usc-')]), ('State, DC and territorial constitutional snapshots', [a for a in items if a['id'].startswith('jurisdiction-')])]
        elif identifier == 'learning-home':
            groups = [('Core Knowledge teaching resources', [a for a in items if a['id'].startswith('curriculum-ck-')]), ('OpenStax textbooks', [a for a in items if a['id'].startswith('curriculum-openstax-')])]
        elif identifier == 'repairs-maintenance':
            groups = [('iFixit illustrated repair archive', [a for a in items if a['id'].startswith('ifixit')]), ('Practical repairs and maintenance', [a for a in items if a['id'].startswith('family-')]), ('Vehicle owner manuals and quick guides', [a for a in items if a['id'].startswith(('accord-', 'civic-'))])]
        grouped = {a['id'] for _, entries in groups for a in entries}
        other = [a for a in items if a['id'] not in grouped]
        if other:groups.insert(0, ('Saved content', other))
        for title, entries in groups:
            if not entries:continue
            out += ['', '::: details ' + title + ' (' + str(len(entries)) + (' item)' if len(entries) == 1 else ' items)'), '']
            for asset in entries:
                target = data.get('dashboard', {}).get('asset_links', {}).get(asset['id'])
                if not target:
                    target = ('http://dataark:' + str(data['system'].get('services', {}).get('kiwix_port', 8080)) + '/content/' + quote(Path(asset['relative_path']).stem, safe='')) if asset['relative_path'].endswith('.zim') else '/library-files/' + quote(asset['relative_path'], safe='/')
                publisher = asset.get('online_url') or asset.get('download_url')
                out.append('- [' + asset['title'].replace('[', '(').replace(']', ')') + '](' + target + ')' + (' — [publisher](' + publisher + ')' if publisher else '') + ('' if asset['available'] else ' — currently not installed'))
            out += ['', ':::']
        if identifier in GAPS:
            out += ['', '### Outstanding acquisition gaps', ''] + ['- ' + gap for gap in GAPS[identifier]]
    out += ['', '## Scope and maintenance', '', 'This guide documents registered collections and linked tools. The Community board is a separate local service, outside the content-source card count. USA.gov is an online-only reference and is not presented as an installed collection. Unregistered files and every article/book inside a ZIM are outside this item-level inventory. The wider [content-gap register](../20-Administration/ContentGaps.md) records acquisition work; use Manage Library and the catalogue source logs for current status.', '']
    return '\n'.join(line.rstrip() for line in out), ids, cards

def main():
    data = load_manifest(ROOT / 'dataark.yaml')
    text, ids, cards = generate(data, Path(data['system']['base_mount']))
    (ROOT / 'docs/10-User/ContentSources.md').write_text(text)
    print('Documented', len(cards), 'cards and', len(ids), 'content items')

if __name__ == '__main__': main()
