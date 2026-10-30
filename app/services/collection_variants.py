"""Configured alternatives within a collection; never infer alternatives from names."""

def groups(manifest):
    assets={a['id']:a for a in manifest.get('assets',[])}
    result=[];used=set()
    for repo in manifest.get('repositories',[]):
        variants=repo.get('variants',[])
        if not variants:continue
        if not isinstance(variants,list) or len(variants)<2:raise ValueError('Collection variants must list at least two alternatives.')
        ids=set()
        for option in variants:
            if not isinstance(option,dict) or not all(isinstance(option.get(k),str) and option[k].strip() for k in ('id','title','asset_id')):raise ValueError('Each variant needs an id, title and asset_id.')
            asset=assets.get(option['asset_id'])
            if option['id'] in ids or option['asset_id'] in used or not asset or asset.get('repository_id')!=repo['id'] or not asset.get('relative_path','').endswith('.zim'):raise ValueError('Variant identifiers must be unique and reference assets in their own collection.')
            ids.add(option['id']);used.add(option['asset_id'])
        preferred=repo.get('preferred_variant')
        if preferred not in ids:raise ValueError('Collection preferred_variant must name a configured variant.')
        result.append({'id':repo['id'],'title':repo['title'],'preferred':preferred,'variants':[dict(v) for v in variants]})
    return result


def recovery_archives(profile,policy):
    """Choose one enabled alternative; disabled assets stay disabled."""
    archives=profile.get('archives',[]);enabled={a['id'] for a in archives if a.get('enabled',True)}
    excluded=set();seen=set();overrides=policy.get('variant_preferences',{})
    if not isinstance(overrides,dict):raise ValueError('variant_preferences must map collection IDs to variant IDs.')
    groups_=profile.get('variant_groups',[])
    if set(overrides)-{g['id'] for g in groups_}:raise ValueError('Unknown collection in variant_preferences.')
    for group in groups_:
        options=group['variants'];ids=[o['id'] for o in options];members=[o['asset_id'] for o in options]
        if len(set(ids))!=len(ids) or seen.intersection(members) or len(set(members))!=len(members) or not set(members)<={a['id'] for a in archives}:raise ValueError('Invalid recovery variant membership.')
        seen.update(members)
        preferred=overrides.get(group['id'],group['preferred'])
        if preferred not in ids:raise ValueError('Unknown restoration variant: '+str(preferred))
        chosen=next(o['asset_id'] for o in options if o['id']==preferred)
        if group['id'] in overrides and chosen not in enabled:raise ValueError('Requested restoration variant is disabled: '+chosen)
        if chosen not in enabled:chosen=next((m for m in members if m in enabled),None)
        excluded.update(m for m in members if m!=chosen)
    return excluded
