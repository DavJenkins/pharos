#!/usr/bin/env python3
"""Discover bounded, official curriculum PDF sources, caching pages for resumability."""
import hashlib, html, json, re, time
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlsplit, urljoin
ROOT = Path(__file__).resolve().parents[1]
CACHE = Path('/var/lib/dataark/curriculum/discovery')
CFG = json.loads((ROOT/'deploy/reference/curriculum-settings.json').read_text())
UA = 'DataArk offline educational library (+https://github.com/DavJenkins/pharos)'

def fetch(url, fresh=False):
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE/(hashlib.sha256(url.encode()).hexdigest()+'.cache')
    if path.exists() and not fresh: return path.read_bytes(), {}
    time.sleep(CFG['request_delay_seconds'])
    with urlopen(Request(url, headers={'User-Agent':UA}), timeout=50) as response:
        data=response.read(8*1024**2+1)
        if len(data)>8*1024**2: raise ValueError('Discovery page too large')
        headers=dict(response.headers)
    path.write_bytes(data)
    return data, headers

class Links(HTMLParser):
    def __init__(self): super().__init__(); self.items=[]; self.current=None
    def handle_starttag(self, tag, attrs):
        if tag=='a': self.current=[dict(attrs).get('href',''), '']
    def handle_data(self, text):
        if self.current is not None: self.current[1]+=text
    def handle_endtag(self, tag):
        if tag=='a' and self.current is not None: self.items.append(self.current); self.current=None

def describe(unit):
    classes=unit.get('class_list',[])
    grade=[]
    for value in classes:
        if value.startswith('grade-'):
            if 'preschool' in value: grade.append('Preschool')
            elif 'kindergarten' in value: grade.append('K')
            else:
                match=re.search(r'grade(?:-?)([1-8])(?:-|$)', value[len('grade-'):])
                if match:grade.append(match[1])
    title=html.unescape(unit['title']['rendered'])
    if not grade:
        match=re.search(r'Grade ([1-8])',title,re.I)
        if match:grade=[match[1]]
    subject='Other'
    for key,name in [('language-arts','Language arts'),('math','Mathematics'),('history','History & geography'),('science','Science'),('music','Music'),('visual','Visual arts')]:
        if key in ' '.join(classes).lower() or key in title.lower():subject=name;break
    return title, sorted(set(grade)), subject

def main():
    units=[]; errors=[]; seen=set()
    for page in range(1,7):
        url=CFG['core_knowledge_catalogue']+'?per_page=100&page='+str(page)
        try:batch=json.loads(fetch(url)[0])
        except Exception as error:
            errors.append({'source':url,'error':str(error)});break
        if not isinstance(batch,list):raise ValueError('Unexpected curriculum catalogue')
        unique=[u for u in batch if u['id'] not in seen]
        if not unique:raise ValueError('Publisher pagination repeated; discovery stopped')
        units+=unique;seen.update(u['id'] for u in unique)
        if len(batch)<100:break
    records={}
    for index, unit in enumerate(units):
        classes=unit.get('class_list',[])
        if 'language-spanish' in classes and 'language-english' not in classes:continue
        title, grades, subject=describe(unit)
        if not grades and not any(x in title.lower() for x in ['core classics','preschool','kindergarten','teacher']):continue
        try:
            parser=Links();parser.feed(fetch(unit['link'])[0].decode())
            for link,label in parser.items:
                link=urljoin(unit['link'],html.unescape(link))
                parts=urlsplit(link)
                if parts.scheme!='https' or parts.hostname!='www.coreknowledge.org' or not parts.path.lower().endswith('.pdf') or not parts.path.startswith('/wp-content/uploads/'):continue
                identifier='ck-'+hashlib.sha256(link.encode()).hexdigest()[:16]
                roles=[];n=parts.path.lower()
                for pattern, role in [(r'(?:_tg|teacher)', 'Teacher guide'),(r'(?:_sb|_sr|student|reader|workbook)','Student material'),(r'(?:assessment|answer)','Assessment / answers')]:
                    if re.search(pattern,n):roles.append(role)
                if not roles:roles=['Supporting resource']
                context={'unit':title,'unit_id':unit['id'],'grades':grades,'subject':subject,'source_page':unit['link'],'roles':roles}
                if identifier in records:records[identifier]['contexts'].append(context)
                else:records[identifier]={'id':identifier,'publisher':'Core Knowledge Foundation','title':title+' - '+', '.join(roles),'url':link,'language':'English','relative_path':'curriculum/core-knowledge/'+identifier+'.pdf','contexts':[context],'license_review':'Require the embedded Creative Commons license; preserve all notices.'}
        except Exception as error:errors.append({'unit':title,'source':unit['link'],'error':str(error)})
        if index%25==0:print('Units checked',index+1,'PDF sources',len(records),flush=True)
        if index%20==0: save(records,errors,units)
    books=json.loads(fetch(CFG['openstax_catalogue'])[0])['books']
    for book in books:
        link=book.get('pdf_url')
        if book.get('book_state')!='live' or not book.get('k12subject') or not link:continue
        parts=urlsplit(link)
        if parts.scheme!='https' or parts.hostname!='assets.openstax.org' or not parts.path.lower().endswith('.pdf'):continue
        identifier='openstax-'+str(book['id'])
        records[identifier]={'id':identifier,'publisher':'OpenStax','title':book['title'],'url':link,'language':'English','relative_path':'curriculum/openstax/'+identifier+'.pdf','contexts':[{'unit':book['title'],'unit_id':book['id'],'grades':['High school / advanced'],'subject':', '.join(book.get('subjects',[])),'source_page':'https://openstax.org/details/'+book['slug'],'roles':['Textbook / exercises']}],'license_review':'Require the embedded open license; no restricted instructor resources.'}
    save(records,errors,units,complete=True)
    print('Discovery complete:',len(records),'PDF sources;',len(errors),'discovery issues',flush=True)

def save(records, errors, units, complete=False):
    obj={'schema':1,'discovery_complete':complete,'scope':'English Core Knowledge public units and OpenStax live K-12-tagged textbooks','records':list(records.values()),'discovery_errors':errors,'units_discovered':len(units),'sources':[CFG['core_knowledge_catalogue'],CFG['openstax_catalogue']]}
    p=ROOT/'deploy/reference/curriculum-catalogue.json';tmp=p.with_suffix('.part');tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n');tmp.replace(p)
if __name__=='__main__':main()
