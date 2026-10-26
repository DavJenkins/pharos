"""Presentation-only card grouping; collection ownership and update recipes stay stable."""
def validate(data, error, check_url):
 cfg=data.get('dashboard',{})
 if not isinstance(cfg,dict) or set(cfg)-{'cards','merged_resource_titles','asset_links'}:raise error('Unsupported dashboard configuration')
 if not isinstance(cfg.get('cards',[]),list) or not isinstance(cfg.get('asset_links',{}),dict):raise error('Dashboard cards must be a list and asset_links a mapping')
 repos={r['id'] for r in data.get('repositories',[])};assets={a['id'] for a in data.get('assets',[])};ids=set();assigned=set()
 for card in cfg.get('cards',[]):
  if not isinstance(card,dict) or set(card)-{'id','anchor','title','description','repository_ids','asset_ids','links','link_groups','artwork_from','collapse_assets'}:raise error('Unsupported dashboard card settings')
  if not isinstance(card.get('id'),str) or card['id'] in ids:raise error('Dashboard card IDs must be unique')
  ids.add(card['id'])
  if card.get('anchor') not in repos:raise error('Unknown dashboard anchor')
  if not isinstance(card.get('title'),str) or not card['title'].strip():raise error('Dashboard cards need titles')
  for key,known in [('repository_ids',repos),('asset_ids',assets)]:
   values=card.get(key,[])
   if not isinstance(values,list) or any(v not in known for v in values) or len(set(values))!=len(values):raise error('Unknown or duplicate dashboard '+key)
  for identifier in card.get('asset_ids',[]):
   if identifier in assigned:raise error('An asset is explicitly assigned to multiple dashboard cards')
   assigned.add(identifier)
  if card.get('artwork_from',card['anchor']) not in repos:raise error('Unknown dashboard artwork source')
  if type(card.get('collapse_assets',True)) is not bool:raise error('Dashboard collapse_assets must be boolean')
  groups=card.get('link_groups',[])
  if not isinstance(groups,list):raise error('Dashboard link groups must be a list')
  for group in groups:
   if not isinstance(group,dict) or set(group)!={'title','links'} or not isinstance(group['title'],str):raise error('Invalid dashboard link group')
  if not isinstance(card.get('links',[]),list) or any(not isinstance(g.get('links'),list) for g in groups):raise error('Dashboard links must be lists')
  links=card.get('links',[])+[link for group in groups for link in group['links']]
  for link in links:
   if not isinstance(link,dict) or not isinstance(link.get('title'),str):raise error('Invalid dashboard link')
   if link.get('service')=='kiwix':check_url(link.get('path','/'))
   else:check_url(link.get('url'))
 for key,target in cfg.get('asset_links',{}).items():
  if key not in assets:raise error('Unknown dashboard asset link')
  check_url(target)
 if not isinstance(cfg.get('merged_resource_titles',[]),list) or any(not isinstance(x,str) for x in cfg.get('merged_resource_titles',[])):raise error('Invalid merged resource titles')

def compose(data, rows):
 cfg=data.get('dashboard',{});cards=cfg.get('cards',[])
 if not cards:return data.get('repositories',[]),rows
 repos={r['id']:r for r in data['repositories']};explicit={a for c in cards for a in c.get('asset_ids',[])};consumed={rid for c in cards for rid in c.get('repository_ids',[])};lookup={a['id']:a for group in rows.values() for a in group}
 result=[];display_rows={}
 for repo in data['repositories']:
  anchored=[c for c in cards if c['anchor']==repo['id']]
  if anchored:
   for card in anchored:
    merged={**repo,**card,'artwork':repos[card.get('artwork_from',card['anchor'])].get('artwork'),'collapse_assets':card.get('collapse_assets',True),'links':card.get('links',[])}
    items=[a for rid in card.get('repository_ids',[]) for a in rows.get(rid,[]) if a['id'] not in explicit]
    items += [lookup[a] for a in card.get('asset_ids',[]) if a in lookup]
    result.append(merged);display_rows[card['id']]=items
  elif repo['id'] not in consumed:
   result.append(repo);display_rows[repo['id']]=[a for a in rows.get(repo['id'],[]) if a['id'] not in explicit]
 return result,display_rows
