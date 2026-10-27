#!/usr/bin/env python3
"""Install the recorded public curriculum PDFs; never delete saved content."""
import concurrent.futures, threading
import argparse, fcntl, hashlib, html, json, os, re, shutil, subprocess, sys, tempfile, time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.request import Request, urlopen
from urllib.parse import urlsplit, quote
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.services.manifest import atomic_write
from tools.update_worker import report
CONTENT=Path('/mnt/storage')
CATALOGUE=ROOT/'deploy/reference/curriculum-catalogue.json'
UA='DataArk offline educational library (+https://github.com/DavJenkins/pharos)'
REQUEST_LOCK=threading.Lock()
LAST_REQUEST=0

def validate_item(item):
    path=PurePosixPath(item['relative_path'])
    if not re.fullmatch(r'(ck-[a-f0-9]{16}|openstax-[0-9]+)',item['id']):raise ValueError('Invalid curriculum identifier')
    if str(path) not in ('curriculum/core-knowledge/'+item['id']+'.pdf','curriculum/openstax/'+item['id']+'.pdf'):raise ValueError('Invalid curriculum path')
    url=urlsplit(item['url'])
    if url.scheme!='https' or url.hostname not in ('www.coreknowledge.org','assets.openstax.org') or url.username or url.password or not url.path.lower().endswith('.pdf'):raise ValueError('Invalid publisher URL')

def checksum(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
    return h.hexdigest()

def inspect_pdf(path, publisher):
    with path.open('rb') as stream:
        if stream.read(5)!=b'%PDF-':raise ValueError('Publisher did not return a PDF')
    info=subprocess.check_output(['pdfinfo',str(path)],text=True,stderr=subprocess.STDOUT,timeout=30)
    pages=int(re.search(r'^Pages:\s+(\d+)',info,re.M)[1])
    text=subprocess.check_output(['pdftotext','-f','1','-l',str(min(pages,10)),str(path),'-'],text=True,stderr=subprocess.DEVNULL,timeout=45)
    flat=' '.join(text.split())
    if not re.search(r'(?:licensed|licens(?:e|ing)|copyright).{0,160}Creative Commons|Creative Commons.{0,180}(?:Attribution|CC BY)',flat,re.I):raise ValueError('Open license not established in front matter; needs review')
    license='Creative Commons; preserve the exact license and notices in this PDF'
    if 'NonCommercial' in flat or 'Noncommercial' in flat or 'Non-Commercial' in flat or 'Non Commercial' in flat or 'BY-NC' in flat:license+=' (noncommercial)'
    return pages,license,flat[:600]

def acquire(item, previous, cfg):
    validate_item(item);target=CONTENT/item['relative_path'];record=dict(item)
    record['checked_at']=datetime.now(timezone.utc).isoformat()
    if target.is_file() and previous.get('sha256') and checksum(target)==previous['sha256']:
        return {**record,**{k:previous[k] for k in ['sha256','bytes','pages','license','header'] if k in previous},'status':'installed'}
    stage=CONTENT/'.curriculum-staging'/(item['id']+'.pdf.part');stage.parent.mkdir(parents=True,exist_ok=True)
    try:
        limit=cfg['max_file_mib']*1024**2
        global LAST_REQUEST
        with REQUEST_LOCK:
            time.sleep(max(0,cfg['request_delay_seconds']-(time.monotonic()-LAST_REQUEST)))
            LAST_REQUEST=time.monotonic()
        with urlopen(Request(quote(item['url'],safe=':/%?=&'),headers={'User-Agent':UA}),timeout=60) as response,stage.open('wb') as output:
            final=urlsplit(response.url)
            if final.scheme!='https' or final.hostname not in ('www.coreknowledge.org','assets.openstax.org'):raise ValueError('Unexpected publisher redirect')
            size=0
            while True:
                block=response.read(1024**2)
                if not block:break
                size+=len(block)
                if size>limit:raise ValueError('Publisher PDF exceeds configured file limit')
                if shutil.disk_usage(CONTENT).free-len(block)<cfg['reserve_gib']*1024**3:raise ValueError('Content-drive reserve reached')
                output.write(block)
        pages,license,header=inspect_pdf(stage,item['publisher'])
        target.parent.mkdir(parents=True,exist_ok=True);stage.chmod(0o644);sha=checksum(stage);size=stage.stat().st_size
        expected=item.get('sha256') or previous.get('sha256')
        if expected and sha!=expected:raise ValueError('Publisher edition differs from the recorded hash; needs review')
        stage.replace(target)
        record.update(status='installed',pages=pages,license=license,header=header,bytes=size,sha256=sha)
    except Exception as error:
        if target.is_file() and previous.get('status')=='installed':return {**previous,'last_check_error':str(error)}
        record.update(status='needs_review',error=str(error))
    return record

def coverage(records):
    units={}
    for record in records:
        for context in record.get('contexts',[]):
            key=(record['publisher'],context['unit_id'])
            unit=units.setdefault(key,{'title':context['unit'],'publisher':record['publisher'],'grades':context['grades'],'subject':context['subject'],'topics':context.get('topics',[]),'expected':set(),'installed':set(),'roles':set()})
            unit['expected'].add(record['id'])
            if record.get('status')=='installed':unit['installed'].add(record['id']);unit['roles'].update(context['roles'])
    result=[]
    for unit in units.values():
        result.append({**{k:v for k,v in unit.items() if k not in ('expected','installed','roles')},'expected_files':len(unit['expected']),'installed_files':len(unit['installed']),'roles':sorted(unit['roles']),'all_discovered_files_installed':bool(unit['expected']) and unit['expected']==unit['installed'],'teacher_and_student':'Teacher guide' in unit['roles'] and 'Student material' in unit['roles']})
    return result

def publish(records, catalogue):
    e=html.escape;directory=CONTENT/'curriculum';directory.mkdir(exist_ok=True)
    units=coverage(records)
    atomic_write(directory/'sources.json',(json.dumps(records,ensure_ascii=False,indent=2)+'\n').encode())
    atomic_write(directory/'coverage.json',(json.dumps({'units':units,'discovery_errors':catalogue.get('discovery_errors',[]),'note':'All discovered PDFs installed is not proof of a complete grade or accredited programme.'},ensure_ascii=False,indent=2)+'\n').encode())
    installed=[r for r in records if r.get('status')=='installed']
    out=['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Curriculum library - Data Ark</title><style>.curriculum-unit a,.curriculum-unit p{overflow-wrap:anywhere}.curriculum-unit li{margin:.6rem 0}.curriculum-unit li span{display:block;font-size:.85rem;color:#526471}table{border-collapse:collapse}th,td{padding:.6rem;text-align:left;vertical-align:top;border-bottom:1px solid #c5c3b8;min-width:140px}th:first-child{min-width:65px}</style><link rel="stylesheet" href="/assets/css/activities.css"></head><body><nav><a href="/">Library</a> · <a href="/learning.html">Learning at home</a></nav><header><p class="eyebrow">TEACH, LEARN AND KEEP GOING</p><h1>Curriculum library</h1><p>Original teacher guides, student books, lessons and textbooks stored on the Ark. '+str(len(installed))+' verified PDFs installed. English-language collection.</p></header><main><section class="panel"><h2>Understand the coverage</h2><p>Core Knowledge units and OpenStax textbooks are learning materials, not enrolment in an accredited school. Coverage below counts discovered unit packages, not a certified complete K-12 programme. OpenStax books on the high-school/advanced shelf are not assigned to a particular grade. Instructor-only resources and paid services are not included.</p><p><a href="coverage.json">Detailed coverage data</a> · <a href="sources.json">Source editions and file hashes</a></p></section><section class="panel"><h2>Grade and subject coverage</h2><div style="overflow-x:auto"><table><thead><tr><th>Level</th><th>Mathematics</th><th>Language arts</th><th>Science</th><th>History &amp; geography</th></tr></thead><tbody>']
    for grade in ['Preschool','K']+[str(n) for n in range(1,13)]:
        out.append('<tr><th>'+e(grade)+'</th>')
        for subject in ['Mathematics','Language arts','Science','History & geography']:
            matching=[u for u in units if grade in u['grades'] and u['subject']==subject]
            if grade.isdigit() and 9<=int(grade)<=12:
                terms={'Mathematics':['math','algebra','geometry','calculus','statistics'],'Language arts':['writing','english','composition','literature'],'Science':['science','biology','chemistry','physics','astronomy'],'History & geography':['history','geography','government','social studies']}[subject]
                shelf=[u for u in units if u['publisher']=='OpenStax' and u['installed_files'] and any(term in (' '.join(u.get('topics',[]))+' '+u['title']).lower() for term in terms)]
                text=str(len(shelf))+' shared textbooks; grade sequence not assigned' if shelf else 'Gap: no matching textbook installed'
            elif not matching:text='Gap: no unit discovered'
            else:
                ready=sum(u['all_discovered_files_installed'] for u in matching);paired=sum(u['teacher_and_student'] for u in matching)
                text=str(ready)+'/'+str(len(matching))+' discovered unit packages installed; '+str(paired)+' with teacher + student material'
            out.append('<td>'+e(text)+'</td>')
        out.append('</tr>')
    out+=['</tbody></table></div><p>Package counts describe this snapshot only. Missing grades, subjects, teaching components and download issues remain gaps; a textbook alone is not a sequenced course. Use the unit list to inspect what each package actually contains.</p></section><section class="panel"><h2>Find material</h2><label>Filter by title, grade, subject or role <input id="curriculum-search" type="search"></label><p id="filter-count" aria-live="polite"></p></section>']
    grouped=defaultdict(list)
    for record in records:
        for context in record.get('contexts',[]):grouped[(record['publisher'],context['unit_id'],context['unit'])].append((record,context))
    for (publisher,uid,title),entries in sorted(grouped.items(),key=lambda x:(x[0][0],x[1][0][1]['grades'],x[1][0][1]['subject'],x[0][2])):
        c=entries[0][1];labels=', '.join(c['grades'])+' | '+c['subject']+' | '+publisher
        out+=['<section class="panel curriculum-unit"><h2>'+e(title)+'</h2><p>'+e(labels)+'</p><ul>']
        for record,context in entries:
            title=', '.join(context['roles'])+' - '+Path(urlsplit(record['url']).path).name
            if record.get('status')=='installed':out.append('<li><a href="/library-files/'+quote(record['relative_path'],safe='/')+'">'+e(title)+'</a> ('+str(record['pages'])+' pages) <span>'+e(record['license'])+'</span></li>')
            else:out.append('<li>'+e(title)+' - not installed: '+e(record.get('error','Awaiting download'))+'</li>')
        out+=['</ul><p>Source: '+e(entries[0][1]['source_page'])+'</p></section>']
    out+=['<section class="panel"><h2>Licenses and preservation</h2><p>Original PDFs are unchanged. Preserve their embedded attribution, images, third-party notices and license terms. Core Knowledge materials may require noncommercial use and share-alike; they are not permission to sell the collection. OpenStax licenses vary by title. No publisher endorsement or accreditation is claimed.</p><p>Discovery issues: '+str(len(catalogue.get('discovery_errors',[])))+'. They are retained in the coverage data rather than hidden.</p></section></main><script src="/assets/js/curriculum.js"></script></body></html>']
    atomic_write(directory/'index.html','\n'.join(out).encode())
    return len(installed),len(units)

def register(records):
    import yaml
    data=yaml.safe_load((ROOT/'dataark.yaml').read_text())
    repo={'id':'curriculum','category':'content_sources','title':'Structured curriculum resources','description':'Core Knowledge teacher and student units and OpenStax textbooks; coverage by grade and subject.','artwork':{'path':'app/static/assets/icons/Family.png','alt':'Learning collection'},'collapse_assets':True,'update_policy':'manual','refresh_interval':'never','links':[{'title':'Browse curriculum and coverage','url':'/library-files/curriculum/index.html'}]}
    if not any(r['id']=='curriculum' for r in data['repositories']):data['repositories'].append(repo)
    old={a['id']:a for a in data['assets']}
    for record in records:
        if record.get('status')!='installed':continue
        asset={'id':'curriculum-'+record['id'],'repository_id':'curriculum','category':'pdf_reference','title':record['title'],'relative_path':record['relative_path'],'service_endpoint':'/library-files/'+record['relative_path'],'update_policy':'manual','refresh_interval':'never','expected_hash':record['sha256'],'download_url':record['url'],'online_url':record['contexts'][0]['source_page'],'source_note':record['license']+'; original PDF; '+str(record['pages'])+' pages.'}
        if old.get(asset['id'],{}).get('removed'):continue
        data['assets']=[a for a in data['assets'] if a['id']!=asset['id']]+[asset]
    card=next(c for c in data['dashboard']['cards'] if c['id']=='learning-home')
    if 'curriculum' not in card.setdefault('repository_ids',[]):card['repository_ids'].append('curriculum')
    if not any(l.get('url')=='/library-files/curriculum/index.html' for l in card['links']):card['links'].insert(0,{'title':'Curriculum library and coverage','url':'/library-files/curriculum/index.html'})
    card['description']='Teacher guides, student materials and textbooks organized by grade and subject, alongside learning activities for all ages. Coverage and gaps are identified.'
    atomic_write(ROOT/'dataark.yaml',yaml.safe_dump(data,sort_keys=False,allow_unicode=True).encode())

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');parser.add_argument('--index-only',action='store_true');args=parser.parse_args()
    cfg=json.loads((ROOT/'deploy/reference/curriculum-settings.json').read_text());cat=json.loads(CATALOGUE.read_text());items=cat['records']
    if not args.apply and not args.index_only:print('Preview:',len(items),'PDF sources. Use --apply to acquire.');return
    if not CONTENT.is_mount():raise SystemExit('Content SSD is not mounted')
    lock=Path('/var/lib/dataark/curriculum/worker.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    state=CONTENT/'curriculum/sources.json';previous={r['id']:r for r in json.loads(state.read_text())} if state.exists() else {}
    if args.index_only:publish(list(previous.values()),cat);register(list(previous.values()));return
    update_lock=Path('/var/lib/dataark/updates/worker.lock').open('a');__import__('tools.content_lock',fromlist=['acquire']).acquire(update_lock)
    records=[];used=0;number=0;seen=set();started=time.monotonic()
    while True:
        if time.monotonic()-started>5400:raise ValueError('Curriculum run limit reached; saved progress retained')
        if number>=len(items):
            cat=json.loads(CATALOGUE.read_text())
            additions=[item for item in cat['records'] if item['id'] not in seen]
            if additions:items+=additions
            elif cat.get('discovery_complete'):
                current={item['id']:item for item in cat['records']}
                for record in records:
                    if record['id'] in current:record['contexts']=current[record['id']]['contexts']
                break
            else:
                report('downloading','Curriculum library',None,str(len(records))+' resources processed; discovering additional units')
                time.sleep(5);continue
        batch=items[number:number+20]
        report('downloading','Curriculum library',100*number/max(1,len(items)) if cat.get('discovery_complete') else None,str(number)+'/'+str(len(items))+' discovered files processed; fetching next '+str(len(batch)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            results=pool.map(lambda item:acquire(item,previous.get(item['id'],{}),cfg),batch)
            for item,record in zip(batch,results):
                number+=1;seen.add(item['id']);records.append(record);used+=record.get('bytes',0)
                print(record.get('status'),item['id'],record.get('error',''),flush=True)
                if used>cfg['max_collection_gib']*1024**3:raise ValueError('Configured collection size limit reached')
        publish(records,cat)
    ready,units=publish(records,cat);register(records)
    failed=len(records)-ready
    report('idle',detail='Curriculum: '+str(ready)+' verified PDFs, '+str(units)+' discovered units; '+str(failed)+' files need review.')
    print('Curriculum installation finished',ready,'installed;',failed,'need review',flush=True)
if __name__=='__main__':main()
