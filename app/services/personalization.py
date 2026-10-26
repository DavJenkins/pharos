"""Validate optional household content interests without changing installed selections."""
import re

def validate(data, error, check_url):
    profile = data.get('personalization')
    if profile is None:
        return
    keys = {'version', 'languages', 'jurisdictions_of_interest', 'vehicles', 'destinations'}
    if not isinstance(profile, dict) or set(profile) - keys:
        raise error('Unsupported personalization settings')
    if type(profile.get('version')) is not int or profile['version'] != 1:
        raise error('Personalization version must be 1')
    assets = {asset['id'] for asset in data.get('assets', [])}
    def strings(values, label):
        if not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values):
            raise error('Personalization ' + label + ' must be a list of nonempty strings')
        if len(set(values)) != len(values):
            raise error('Duplicate personalization ' + label)
    for key in ['languages', 'jurisdictions_of_interest']:
        strings(profile.get(key, []), key)
    groups = {
        'vehicles': {'id', 'year', 'make', 'model', 'body_style', 'asset_ids'},
        'destinations': {'id', 'name', 'asset_ids', 'viewer_url'},
    }
    for group, allowed in groups.items():
        entries = profile.get(group, [])
        if not isinstance(entries, list):
            raise error('Personalization ' + group + ' must be a list')
        seen = set()
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) - allowed:
                raise error('Unsupported personalization ' + group + ' entry')
            identifier = entry.get('id')
            if not isinstance(identifier, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]*', identifier) or identifier in seen:
                raise error('Personalization IDs must be unique lowercase slugs within each list')
            seen.add(identifier)
            required = ['make', 'model'] if group == 'vehicles' else ['name']
            for key in required + (['body_style'] if 'body_style' in entry else []):
                if not isinstance(entry.get(key), str) or not entry[key].strip():
                    raise error('Personalization entry needs ' + key)
            if group == 'vehicles' and (type(entry.get('year')) is not int or not 1886 <= entry['year'] <= 2200):
                raise error('Personalization vehicle year must be an integer from 1886 to 2200')
            strings(entry.get('asset_ids', []), 'asset_ids')
            if set(entry.get('asset_ids', [])) - assets:
                raise error('Unknown personalization asset reference')
            if 'viewer_url' in entry:
                check_url(entry['viewer_url'])
                if not entry['viewer_url'].startswith('/') or entry['viewer_url'].startswith('//'):
                    raise error('Personalization viewer must be an Ark-relative URL')
