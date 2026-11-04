"""Declarative demo additions; never rewrite the normal library or an editor draft."""
import copy


def overlay(data, config):
    data = copy.deepcopy(data)
    data['system']['hide_missing'] = False
    data['system']['demo_library'] = {'label': config['label'], 'notice': config['notice'], 'heading': config.get('heading','Try the installed offline sample'), 'repository_id': config['repository']['id'], 'show_sample_link': config.get('show_sample_link', True), 'installed_only_default': config.get('installed_only_default', False)}
    repository = config['repository']
    if not any(r['id'] == repository['id'] for r in data['repositories']):
        data['repositories'].insert(0,copy.deepcopy(repository))
    present = {a['id'] for a in data['assets']}
    for item in config['samples']:
        if item['id'] in present:
            continue  # Keep removal state and caretaker changes.
        asset = {'id': item['id'], 'title': item['title'], 'relative_path': item['path'],
                 'repository_id': repository['id'], 'category': item['category'],
                 'update_policy': 'manual', 'refresh_interval': 'never'}
        if item.get('url'):
            asset.update(download_url=item['url'], expected_hash=item['sha256'])
        data['assets'].append(asset)
    return data
