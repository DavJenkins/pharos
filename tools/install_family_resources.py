#!/usr/bin/env python3
"""Explicitly install/update approved family resources; never uploads or stores personal work.
Run with system Python (python3-reportlab), then deploy/deploy-web.sh to publish links.
Re-running reinstates listed files. Publisher failures retain verified existing copies.
"""
import argparse,concurrent.futures,hashlib,html,io,json,os,re,subprocess,sys,tempfile,urllib.request,zipfile
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
CONTENT=Path('/mnt/storage/family-resources');CATALOGUE=ROOT/'deploy/reference/family-catalogue.json'
def atomic(path,data):
 path.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as f:f.write(data);temp=Path(f.name)
 temp.chmod(0o644);temp.replace(path)
def download(item):
 item=dict(item);item['filename']=item['collection']+'/'+item['id']+'.'+item['format'];item['checked_at']=datetime.now(timezone.utc).isoformat();dest=CONTENT/item['filename']
 try:
  req=urllib.request.Request(item['url'],headers={'User-Agent':'Mozilla/5.0 (Data Ark offline educational archive)'})
  with urllib.request.urlopen(req,timeout=45) as r:data=r.read(30*1024**2+1);item['resolved_url']=r.url
  if len(data)>30*1024**2:raise ValueError('Publisher file exceeds 30 MiB limit')
  if item['format']=='pdf':
   if not data.startswith(b'%PDF-'):raise ValueError('Publisher did not return a PDF')
   with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
    f.write(data);f.flush();info=subprocess.check_output(['pdfinfo',f.name],text=True,stderr=subprocess.STDOUT);item['pages']=int(re.search(r'^Pages:\s+(\d+)',info,re.M)[1]);text=subprocess.check_output(['pdftotext','-f','1','-l','2',f.name,'-'],text=True,stderr=subprocess.DEVNULL)
   item['document_header']=' '.join(text.split())[:600]
  else:
   with zipfile.ZipFile(io.BytesIO(data)) as z:
    if 'word/document.xml' not in z.namelist() or any('vbaproject' in n.lower() for n in z.namelist()):raise ValueError('Not a macro-free Word document')
    from xml.etree import ElementTree as ET
    text=' '.join(''.join(ET.fromstring(z.read(n)).itertext()) for n in z.namelist() if re.match(r'word/(document|footer\d*|header\d*)\.xml$',n))
    if len(text.strip())<100:raise ValueError('Empty agreement')
    expected={'cp-contractor':'TERMS AND CONDITIONS','cp-amendment':'Amendment','cp-sow':'SOW'}[item['id']]
    if expected not in text:raise ValueError('Expected agreement title missing')
    item['document_header']=' '.join(text.split())[:600]
  atomic(dest,data);item.update(status='installed',bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
 except Exception as e:
  item.update(status='unavailable',error=str(e));old=CONTENT/'sources.json'
  if dest.is_file() and old.is_file():
   previous=next((p for p in json.loads(old.read_text()) if p['id']==item['id'] and p.get('sha256')==hashlib.sha256(dest.read_bytes()).hexdigest()),None)
   if previous:item={**previous,'last_check_error':str(e),'checked_at':item['checked_at']}
 print(item['status'],item['id'],item.get('error',''),flush=True);return item
def write_index(records):
 e=html.escape
 page=['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Family activities & readiness — Data Ark</title><link rel="stylesheet" href="/assets/css/activities.css?v=20261023-family1"></head><body><nav><a href="/">Library</a> · <a href="/activities.html">Play & color</a> · <a href="/printables.html">Paper & worksheets</a> · <a href="/library-files/forms/index.html">Official forms</a></nav><header><p class="eyebrow">SOMETHING FOR THE WHOLE HOUSEHOLD</p><h1>Activity books & readiness</h1><p>Books and practical records stored on the Ark. Read on screen or print selected pages. English and Spanish resources are labeled below.</p></header><main><section class="panel"><h2>Find a resource</h2><div class="controls"><label>Search title or purpose<input id="resource-search" type="search"></label><label>Language<select id="resource-language"><option value="">All languages</option><option>English</option><option>Spanish</option></select></label><label>Purpose<select id="resource-group"><option value="">All purposes</option><option value="kids">Children & activities</option><option value="adult-coloring">Adult coloring</option><option value="holiday-coloring">Holiday coloring</option><option value="cookbooks">Cooking & pantry meals</option><option value="food-preservation">Food preservation & emergency cooking</option><option value="drinking-water">Drinking water</option><option value="shelter-winter">Shelter & winter readiness</option><option value="first-aid-care">First aid & caregiving</option><option value="growing-food">Growing food</option><option value="repairs">Repairs & maintenance</option><option value="navigation-field">Navigation & field skills</option><option value="emergency-comms">Emergency communications</option><option value="animals-emergency">Pets & livestock</option><option value="sanitation">Sanitation & hygiene</option><option value="readiness">Readiness & coordination</option><option value="contracts">Agreements</option><option value="generated">Paper & household worksheets</option></select></label></div><p id="resource-count" role="status"></p></section>']
 for group,title in [('kids','Coloring, puzzles & learning'),('adult-coloring','Adult coloring — art, nature & detailed designs'),('holiday-coloring','Holiday coloring — family and detailed designs'),('cookbooks','Cookbooks & pantry meals'),('food-preservation','Food preservation & emergency cooking'),('drinking-water','Drinking water: sources, storage & treatment'),('shelter-winter','Shelter, heating & winter readiness'),('first-aid-care','First aid & caregiving when help is delayed'),('growing-food','Growing food: New England gardens'),('repairs','Practical repairs & maintenance'),('navigation-field','Navigation & field skills'),('emergency-comms','Emergency communications & coordination'),('animals-emergency','Pets & livestock during emergencies'),('sanitation','Sanitation & hygiene during utility outages'),('readiness','Readiness & coordination'),('contracts','Agreements & project templates'),('generated','Paper & household worksheets')]:
  page.append('<section class="panel resource-section" id="'+group+'"><h2>'+title+'</h2>')
  if group=='kids':page.append('<p>Books can be read on screen. For coloring and written activities, print a page or use the <a href="/coloring.html">PDF coloring tool</a> where the book permits it. Suggested audiences are browsing aids, not formal age ratings. Some books need adult help.</p>')
  if group=='drinking-water':page.append('<p>Original references for water sources, storage, rainwater collection, treatment selection and well testing. Boiling and disinfection do not remove all chemical contamination. Use each guide within its stated limits; rainwater guidance is regional and historical. <a href="#food-preservation">Related FEMA and FDA food-and-water guides</a>.</p>')
  if group=='shelter-winter':page.append('<p>Original guides for winter outages, staying warm, home heating, generator hazards, weatherstripping and frozen pipes. Historical editions and regional scope are identified. Keep combustion equipment within its rated use; never use outdoor equipment to heat an enclosed shelter. Weatherization guidance is for preparation, not structural-damage assessment.</p>')
  if group=='first-aid-care':page.append('<p>Original first-aid references, medication records and caregiver planning guides. Start with the shorter bleeding-control booklet or planning workbooks; the IFRC volume is a comprehensive evidence reference. Seek emergency help when available and use skills within your training. Save completed health records on your own device, not in the shared library. NYC workbooks retain city-specific services and contacts.</p>')
  if group=='growing-food':page.append('<p>New England planting, vegetable varieties, seed saving, soil-building and pest identification. Adjust dates to local frost, elevation and season. Archived handbooks and pest guides preserve their original references; pesticide labels and current local requirements take precedence. <a href="#food-preservation">Preserve the harvest</a>.</p>')
  if group=='repairs':page.append('<p>Short guides for bike flats, clothing repairs, leak checks, electrical inspection, tool safety and small-engine maintenance. These supplement the installed <a href="http://dataark:8080/content/ifixit_en_all_2025-12">iFixit repair library</a>. Engine-specific manuals take precedence over the generic schedule. Electrical material covers inspection and hazard recognition, not permission to work on live circuits.</p>')
  if group=='navigation-field':page.append('<p>Map symbols, compass and GPS skills, coordinates, route planning and outdoor emergency preparation. Check map datum, scale and current magnetic declination. US National Grid coordinates differ from amateur-radio Maidenhead grid squares. Archived training examples are labeled. <a href="/library-files/maps/index.html">Local maps</a> · <a href="/library-files/resilience/index.html">Existing map-and-compass and field references</a>.</p>')
  if group=='emergency-comms':page.append('<p>Radio messages, plain-language procedures, volunteer coordination and family contact plans. Use the existing <a href="readiness/fema-ics.pdf">FEMA incident forms</a> for communications plans, messages and activity logs. Agree on check-in times, a backup contact and meeting places before an outage; keep personal plans on your own device. Archived radio procedures do not override current rules or the serving organization.</p>')
  if group=='animals-emergency':page.append('<p>Pet evacuation and shelter planning, animal supplies and sanitation, farm preparedness, poultry biosecurity and blank cattle-care handover forms. English and Spanish pet guides are included. NYC services and shelter rules are regional; animal movement restrictions and veterinary instructions take precedence. Keep completed animal records and personal contacts on your own device.</p>')
  if group=='sanitation':page.append('<p>Original guides for emergency toilets, low-water handwashing, household cleanup and rodent prevention. Regional toilet and waste-disposal guidance is identified; follow local public-health and wastewater instructions. English and Spanish bucket labels are ready to print.</p>')
  if group=='food-preservation':page.append('<p>Original USDA, FDA, FEMA and extension references for canning, fermentation, drying, pantry storage and cooking during outages. Read complete tested procedures, including equipment and altitude requirements. Editions are shown below; the FDA outage guide is January 2023 and the FEMA booklet is an August 2004 archive. <a href="#cookbooks">Cookbooks and pantry meal plans</a>.</p>')
  if group=='cookbooks':page.append('<p>Cookbooks for everyday meals and pantry-based cooking, available offline or to print. Prices and policy references retain their original publication dates. Preserve each book’s credits and usage terms.</p>')
  if group=='holiday-coloring':page.append('<p>Original Ark holiday designs in two packs: simpler family pages and detailed patterns for adults and teens. Each pack has 14 themes. Open either in the <a href="/coloring.html">PDF coloring tool</a> or print selected pages. Freely copy, color and share.</p>')
  if group=='adult-coloring':page.append('<p>Detailed botanical, architectural and art collections for adults and teens. Print a page or open a book in the <a href="/coloring.html">PDF coloring tool</a>. Preserve each page’s source and license when sharing colored versions.</p>')
  if group=='readiness':page.append('<p>The FEMA booklet includes ICS 201–225 forms and completion instructions, including radio plans, general messages (213), activity logs (214), check-ins and resource records. Its archived September 2010 edition is labeled; follow the forms and procedures required by your organization. <a href="/library-files/preparedness/index.html">Existing FEMA, CERT & preparedness guides</a>.</p>')
  if group=='contracts':page.append('<p>Common Paper templates, CC BY 4.0. Download Word files to edit. The Statement of Work accompanies the Professional Services Agreement in <a href="/library-files/forms/index.html">Forms & Templates</a>. Preserve standard terms and fill the required business terms. Jurisdiction-specific personal, property and consumer agreements are not supplied as universally valid contracts.</p>')
  page.append('<ul class="book-list">')
  for r in records:
   if r['collection']!=group or r['status']!='installed':continue
   search=e(' '.join(str(r.get(k,'')) for k in ['title','purpose','age','language']).lower(),quote=True)
   page.append('<li data-resource data-form-id="family-'+e(r['id'],quote=True)+'" data-search="'+search+'" data-language="'+e(r['language'],quote=True)+'" data-group="'+group+'"><a data-form-file href="'+e(r['filename'],quote=True)+'">'+e(r['title'])+'</a><div class="tags">'+e(r['language']+' · '+r['age']+' · '+r['purpose'])+'</div><div class="tags">'+e((str(r['pages'])+(' page · ' if r['pages']==1 else ' pages · ') if r.get('pages') else '')+r['format'].upper()+' · '+r.get('edition','Publisher edition retrieved '+r['checked_at'][:10]))+'</div><details><summary>Source, use & edition</summary><p>'+e(r['license'])+'</p><p>'+e(r.get('document_header',''))+'</p><p>Retrieved '+e(r['checked_at'])+' · <a href="'+e(r['source_page'],quote=True)+'">Publisher / source (internet required)</a></p></details></li>')
  page.append('</ul></section>')
 unavailable=[r for r in records if r['status']!='installed']
 if unavailable:
  page.append('<details><summary>Publisher downloads not installed ('+str(len(unavailable))+')</summary><ul>')
  for r in unavailable:page.append('<li>'+e(r['title'])+' — '+e(r['error'])+'</li>')
  page.append('</ul></details>')
 page.append('</main><footer><p><a href="sources.json">Sources, retrieval dates, editions, sizes & SHA-256 hashes</a> · <a href="cc-by-4.0.txt">Common Paper offline license</a> · <a href="/docs/20-Administration/FamilyResources.html">Maintenance guide</a></p><p>NASA, CDC, FEMA and NPS originals retain their notices. Source: CDC. CDC materials are also available free from CDC.gov. Reference to products, companies or services does not imply endorsement by CDC, HHS or the U.S. Government. No agency endorsement is implied. NPS Cave Scientist booklets are kept unmodified for non-commercial educational use; do not reformat or sell them. Original Ark worksheets and patterns may be freely copied and adapted. Keep completed private records on your own device.</p></footer><script src="/assets/js/forms-availability.js"></script><script src="/assets/js/family-resources.js?v=20261023-family1"></script></body></html>')
 atomic(CONTENT/'index.html',''.join(page).encode())
def register(records):
 import fcntl
 from app.services.manifest import load_manifest,atomic_write
 from tools.library_removal import serialize
 with Path('/var/lib/dataark/updates/worker.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);data=load_manifest(ROOT/'dataark.yaml')
  repo={'id':'family-resources','category':'content_sources','title':'Paper, Play & Family Resources','description':'Offline paper studio, PDF coloring, browser games, adult coloring, activity books, household worksheets and incident forms. English and Spanish selections.','collapse_assets':True,'update_policy':'manual','refresh_interval':'never','links':[{'title':'Learning at home','url':'/learning.html'},{'title':'Paper studio & household templates','url':'/printables.html'},{'title':'Games, drawing & PDF coloring','url':'/activities.html'},{'title':'Cookbooks & pantry meals','url':'/library-files/family-resources/index.html#cookbooks'},{'title':'Browse local books & readiness forms','url':'/library-files/family-resources/index.html'}]}
  existing=next((r for r in data['repositories'] if r['id']==repo['id']),None)
  if existing:
   repo={**existing,**repo}
   data['repositories']=[repo if r['id']==repo['id'] else r for r in data['repositories']]
  else:data['repositories'].append(repo)
  food={'id':'food-preservation','category':'content_sources','title':'Food Preservation & Emergency Cooking','description':'USDA canning guides, fermentation and pickling, drying, pantry storage and emergency food/cooking safety. Original procedures and editions preserved.','collapse_assets':True,'artwork':{'path':'app/static/assets/icons/Resilience.png','alt':'Food resilience collection icon'},'update_policy':'manual','refresh_interval':'never','links':[{'title':'Preservation & emergency cooking guides','url':'/library-files/family-resources/index.html#food-preservation'},{'title':'Cookbooks & pantry meals','url':'/library-files/family-resources/index.html#cookbooks'}]}
  previous=next((r for r in data['repositories'] if r['id']==food['id']),None)
  if previous:data['repositories']=[{**previous,**food} if r['id']==food['id'] else r for r in data['repositories']]
  else:data['repositories'].append(food)
  sanitation={'id':'sanitation','category':'content_sources','title':'Sanitation & Hygiene','description':'Emergency toilets and labels, low-water handwashing, household cleanup, mold references and rodent prevention. Regional guidance and original editions identified.','collapse_assets':True,'artwork':{'path':'app/static/assets/icons/Sanitation.png','alt':'Sanitation and hygiene icon'},'update_policy':'manual','refresh_interval':'never','links':[{'title':'Open sanitation & hygiene guides','url':'/library-files/family-resources/index.html#sanitation'}]}
  previous=next((r for r in data['repositories'] if r['id']==sanitation['id']),None)
  if previous:data['repositories']=[{**previous,**sanitation} if r['id']==sanitation['id'] else r for r in data['repositories']]
  else:data['repositories'].append(sanitation)
  water={'id':'drinking-water','category':'content_sources','title':'Drinking Water','description':'Water sources and storage, rainwater harvesting, emergency disinfection, treatment selection and well testing. Original editions and regional scope identified.','collapse_assets':True,'artwork':{'path':'app/static/assets/icons/Water.png','alt':'Water droplet icon'},'update_policy':'manual','refresh_interval':'never','links':[{'title':'Open drinking water guides','url':'/library-files/family-resources/index.html#drinking-water'}]}
  previous=next((r for r in data['repositories'] if r['id']==water['id']),None)
  if previous:data['repositories']=[{**previous,**water} if r['id']==water['id'] else r for r in data['repositories']]
  else:data['repositories'].append(water)
  winter={'id':'shelter-winter','category':'content_sources','title':'Shelter & Winter Readiness','description':'Winter outages, staying warm, heater and generator safety, weatherization and frozen pipes. Original editions and regional scope identified.','collapse_assets':True,'artwork':{'path':'app/static/assets/icons/Shelter.png','alt':'Shelter and winter icon'},'update_policy':'manual','refresh_interval':'never','links':[{'title':'Open shelter & winter guides','url':'/library-files/family-resources/index.html#shelter-winter'}]}
  previous=next((r for r in data['repositories'] if r['id']==winter['id']),None)
  if previous:data['repositories']=[{**previous,**winter} if r['id']==winter['id'] else r for r in data['repositories']]
  else:data['repositories'].append(winter)
  care={'id':'first-aid-care','category':'content_sources','title':'First Aid & Caregiving','description':'First-aid references, bleeding control, medication records and disaster planning for children, older adults, caregivers and people with disabilities. English and Spanish planning workbooks.','collapse_assets':True,'artwork':{'path':'app/static/assets/icons/Care.png','alt':'Care and first-aid reference icon'},'update_policy':'manual','refresh_interval':'never','links':[{'title':'Open first-aid & caregiving guides','url':'/library-files/family-resources/index.html#first-aid-care'}]}
  previous=next((r for r in data['repositories'] if r['id']==care['id']),None)
  if previous:data['repositories']=[{**previous,**care} if r['id']==care['id'] else r for r in data['repositories']]
  else:data['repositories'].append(care)
  for extra in [
   {'id':'growing-food','title':'Growing Food','description':'New England planting charts, vegetable varieties, seed saving, composting, soils and pest identification. Regional and archived editions identified.','artwork':{'path':'app/static/assets/icons/Garden.png','alt':'Seedling garden icon'}},
   {'id':'repairs','title':'Practical Repairs & Maintenance','description':'Bicycle flats, hand sewing, leak checks, electrical inspection, tool safety and small-engine maintenance. Supplements the local iFixit library.','artwork':{'path':'app/static/assets/icons/Repair.png','alt':'Repair tools icon'}}]:
   extra.update(category='content_sources',collapse_assets=True,update_policy='manual',refresh_interval='never',links=[{'title':'Open '+extra['title'].lower()+' guides','url':'/library-files/family-resources/index.html#'+extra['id']}])
   previous=next((r for r in data['repositories'] if r['id']==extra['id']),None)
   if previous:data['repositories']=[{**previous,**extra} if r['id']==extra['id'] else r for r in data['repositories']]
   else:data['repositories'].append(extra)
  for extra in [
   {'id':'navigation-field','title':'Navigation & Field Skills','description':'Topographic symbols, compass and GPS navigation, US National Grid coordinates, trip plans and outdoor emergency preparation.','artwork':{'path':'app/static/assets/icons/Navigation.png','alt':'Compass navigation icon'}},
   {'id':'emergency-comms','title':'Emergency Communications','description':'Radio message forms and procedures, plain language, volunteer coordination and family contact planning. Complements existing incident forms and radio tools.','artwork':{'path':'app/static/assets/icons/Radio.png','alt':'Radio communications icon'}}]:
   extra.update(category='content_sources',collapse_assets=True,update_policy='manual',refresh_interval='never',links=[{'title':'Open '+extra['title'].lower()+' guides','url':'/library-files/family-resources/index.html#'+extra['id']}])
   previous=next((r for r in data['repositories'] if r['id']==extra['id']),None)
   if previous:data['repositories']=[{**previous,**extra} if r['id']==extra['id'] else r for r in data['repositories']]
   else:data['repositories'].append(extra)
  animals={'id':'animals-emergency','category':'content_sources','title':'Pets & Livestock','description':'Pet evacuation, shelter, supplies and sanitation, farm preparedness, poultry biosecurity and backup-care plans. English and Spanish pet guides.','collapse_assets':True,'artwork':{'path':'app/static/assets/icons/Animals.png','alt':'Animal paw icon'},'update_policy':'manual','refresh_interval':'never','links':[{'title':'Open pet & livestock emergency guides','url':'/library-files/family-resources/index.html#animals-emergency'}]}
  previous=next((r for r in data['repositories'] if r['id']==animals['id']),None)
  if previous:data['repositories']=[{**previous,**animals} if r['id']==animals['id'] else r for r in data['repositories']]
  else:data['repositories'].append(animals)
  for r in records:
   if r['status']!='installed':continue
   repository={'animals-emergency':'animals-emergency','navigation-field':'navigation-field','emergency-comms':'emergency-comms','growing-food':'growing-food','repairs':'repairs','first-aid-care':'first-aid-care','shelter-winter':'shelter-winter','drinking-water':'drinking-water','food-preservation':'food-preservation','sanitation':'sanitation'}.get(r['collection'],'family-resources')
   identifier='family-'+r['id'];asset={'id':identifier,'repository_id':repository,'category':'pdf_reference','title':r['title'],'relative_path':'family-resources/'+r['filename'],'service_endpoint':'/library-files/family-resources/'+r['filename'],'update_policy':'manual','refresh_interval':'never','expected_hash':r['sha256'],'source_note':r.get('edition','')+' '+r['license']+' Retrieved '+r['checked_at']}
   if r.get('url'):asset.update(online_url=r['source_page'],download_url=r['url'])
   data['assets']=[a for a in data['assets'] if a['id']!=identifier]+[asset]
  atomic_write(ROOT/'dataark.yaml',serialize(data).encode())
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--register',action='store_true');a=p.parse_args()
 if not CONTENT.parent.is_mount():raise SystemExit('Content SSD must be mounted')
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:records=list(pool.map(download,json.loads(CATALOGUE.read_text())))
 subprocess.run(['/usr/bin/python3',str(ROOT/'tools/build_print_packs.py')],check=True)
 subprocess.run(['/usr/bin/python3',str(ROOT/'tools/build_holiday_coloring.py')],check=True)
 records.extend(json.loads((CONTENT/'holidays/sources.json').read_text()))
 for file in sorted((CONTENT/'generated').glob('*.pdf')):
  data=file.read_bytes();info=subprocess.check_output(['pdfinfo',str(file)],text=True)
  records.append({'id':file.stem,'title':('Paper pattern pack' if file.name.startswith('paper') else 'Household worksheet pack')+' — '+('A4' if 'a4' in file.stem else 'US Letter'),'collection':'generated','format':'pdf','filename':'generated/'+file.name,'status':'installed','language':'English','age':'All ages / adult records','purpose':'Print selected pages; paper and pencil needed','license':'DEJ Software / Data Ark original. Freely copy and adapt.','source_page':'/printables.html','checked_at':datetime.now(timezone.utc).isoformat(),'bytes':len(data),'pages':int(re.search(r'^Pages:\s+(\d+)',info,re.M)[1]),'sha256':hashlib.sha256(data).hexdigest()})
 atomic(CONTENT/'sources.json',(json.dumps(records,ensure_ascii=False,indent=2)+'\n').encode())
 # Reuse the verified attribution text already preserved with the existing forms.
 license=Path('/mnt/storage/forms/cc-by-4.0.txt')
 if not license.is_file():raise SystemExit('Existing CC BY 4.0 license text is required')
 atomic(CONTENT/'cc-by-4.0.txt',license.read_bytes());write_index(records)
 if a.register:register(records)
 from tools.publish_content import publish
 print('Portable catalogue refreshed:',publish(CONTENT.parent),'files',flush=True)
 print('Installed',sum(r['status']=='installed' for r in records),'of',len(records),'documents',flush=True)
if __name__=='__main__':main()
