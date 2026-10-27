"""Bounded discovery of dated public PDF editions. Never installs or replaces content."""
from datetime import date
import hashlib
from html.parser import HTMLParser
import ipaddress
import json
from pathlib import Path
import re
from string import Formatter
import subprocess
import tempfile
import time
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener

FIELDS={'year','year2','month','day'}

class MissingEdition(Exception):
    pass


def public_url(url, hosts=None):
    p=urlsplit(url)
    if p.scheme!='https' or not p.hostname or p.username or p.password or p.port not in (None,443):raise ValueError('Expected public HTTPS publisher URL')
    try:
        if not ipaddress.ip_address(p.hostname).is_global:raise ValueError('Private publisher addresses are not allowed')
    except ValueError as error:
        if str(error)=='Private publisher addresses are not allowed':raise
    if p.hostname in ('localhost','localhost.localdomain') or p.hostname.endswith(('.local','.lan')):raise ValueError('Local publisher host is not allowed')
    if hosts is not None and p.hostname not in hosts:raise ValueError('Publisher redirect left the allowed host')
    return p.hostname


def template(rule):
    return rule.get('url_template') or rule['directory_template'].rstrip('/')+'/'+rule['filename_template']


def validate(rule):
    if rule.get('kind') not in ('dated_template','index'):raise ValueError('Unknown edition discovery kind')
    if rule.get('period','year') not in ('year','month','day'):raise ValueError('Unknown edition period')
    for key,default,maximum in [('lookback',2,31),('lookahead',1,2),('max_probes',12,32),('max_bytes',16*1024**2,64*1024**2)]:
        v=rule.get(key,default)
        if type(v) is not int or not 0<=v<=maximum:raise ValueError('Unbounded discovery setting: '+key)
    if not rule.get('max_probes',12) or rule.get('lookback',2)+rule.get('lookahead',1)+1>rule.get('max_probes',12):raise ValueError('Date window exceeds request bound')
    fields=set()
    for _,field,spec,conversion in Formatter().parse(template(rule)):
        if field is not None:
            if field not in FIELDS or spec not in ('','02d','04d') or conversion:raise ValueError('Unsupported date placeholder')
            fields.add(field)
    if 'year' not in fields:raise ValueError('Edition template requires year')
    if rule.get('period') in ('month','day') and 'month' not in fields:raise ValueError('Monthly/daily templates require month')
    if rule.get('period')=='day' and 'day' not in fields:raise ValueError('Daily templates require day')
    sample=template(rule).format(year=2026,year2=26,month=10,day=27)
    host=public_url(sample)
    if rule.get('index_url'):public_url(rule['index_url'],{host})
    if rule.get('kind')=='index' and not rule.get('index_url'):raise ValueError('Index discovery requires an explicit index URL')
    if not rule.get('edition_text_pattern'):raise ValueError('A PDF edition-text check is required')
    re.compile(rule['edition_text_pattern'].format(year=2026,year2=26,month=10,day=27))
    if rule.get('action','review')!='review':raise ValueError('Dated publication editions require review; automatic Kiwix updates use their existing pipeline')
    if rule.get('not_found_title_pattern'):
        if len(rule['not_found_title_pattern'])>200:raise ValueError('Not-found title pattern is too long')
        re.compile(rule['not_found_title_pattern'])
    return {host}


def date_fields(value):
    return {'year':value.year,'year2':value.year%100,'month':value.month,'day':value.day}


def period_date(value,period):
    parts=[int(x) for x in value.split('-')]
    if len(parts)!={'year':1,'month':2,'day':3}[period]:raise ValueError('Current edition does not match configured period')
    return date(*(parts+[1]*(3-len(parts))))


def label(value,period):
    return value.isoformat()[:{'year':4,'month':7,'day':10}[period]]


def window(rule,today):
    period=rule.get('period','year');result=[]
    for offset in range(-rule.get('lookback',2),rule.get('lookahead',1)+1):
        if period=='year':d=date(today.year+offset,1,1)
        elif period=='month':
            y,m=divmod(today.year*12+today.month-1+offset,12);d=date(y,m+1,1)
        else:
            from datetime import timedelta
            d=today+timedelta(days=offset)
        result.append(d)
    return sorted(result,reverse=True)


def url_pattern(rule):
    pieces=[];seen=set()
    for literal,field,_,_ in Formatter().parse(template(rule)):
        pieces.append(re.escape(literal))
        if field:
            if field in seen:pieces.append('(?P='+field+')')
            else:
                pieces.append('(?P<'+field+'>'+('[0-9]{4}' if field=='year' else '[0-9]{2}')+')');seen.add(field)
    return re.compile(''.join(pieces)+'$')


class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a' and len(self.links)<5000:
            href=dict(attrs).get('href')
            if href:self.links.append(href)


class PublisherRedirect(HTTPRedirectHandler):
    def __init__(self,hosts):self.hosts=hosts
    def redirect_request(self,request,fp,code,msg,headers,newurl):
        public_url(newurl,self.hosts)
        return super().redirect_request(request,fp,code,msg,headers,newurl)


def fetch(url,hosts,limit,opener,not_found_title_pattern=None):
    public_url(url,hosts)
    with opener(Request(url,headers={'User-Agent':'DataArk edition discovery (+https://github.com/DavJenkins/pharos)'}),timeout=15) as response:
        public_url(response.url,hosts)
        length=response.headers.get('Content-Length')
        if length and int(length)>limit:raise ValueError('Publisher response exceeds discovery limit')
        data=response.read(limit+1)
        if len(data)>limit:raise ValueError('Publisher response exceeds discovery limit')
        if not_found_title_pattern and not data.startswith(b'%PDF-'):
            title=re.search(r'<title[^>]*>(.*?)</title>',data.decode('utf-8',errors='replace'),re.I|re.S)
            if title and re.fullmatch(not_found_title_pattern,title[1].strip(),re.I):raise MissingEdition()
        return data


def pdf_edition(data,rule,d):
    if not data.startswith(b'%PDF-'):raise ValueError('Publisher did not return a PDF')
    with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
        f.write(data);f.flush()
        subprocess.run(['pdfinfo',f.name],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=10,check=True)
        text=subprocess.check_output(['pdftotext','-f','1','-l','1',f.name,'-'],stderr=subprocess.DEVNULL,timeout=10,text=True)
    header=text[:1500]
    if re.search(r'(?i)\bDRAFT\b|not for filing',header):raise ValueError('Draft edition requires separate review')
    if not re.search(rule['edition_text_pattern'].format(**date_fields(d)),header):raise ValueError('PDF does not identify the expected edition')
    return hashlib.sha256(data).hexdigest()


def discover(rule,asset,today=None,opener=None,validator=pdf_edition):
    hosts=validate(rule);today=today or date.today();period=rule.get('period','year');pattern=url_pattern(rule)
    current=period_date(rule['current_edition'],period)
    match=pattern.fullmatch(asset.get('download_url',''))
    if match:
        values=match.groupdict();current=date(int(values['year']),int(values.get('month') or 1),int(values.get('day') or 1))
    allowed=window(rule,today);candidates=[(d,template(rule).format(**date_fields(d))) for d in allowed if d>current]
    opener=opener or build_opener(PublisherRedirect(hosts)).open
    if rule['kind']=='index':
        parser=Links();parser.feed(fetch(rule['index_url'],hosts,1024**2,opener).decode('utf-8',errors='replace'))
        listed={urljoin(rule['index_url'],href) for href in parser.links}
        candidates=[(d,url) for d,url in candidates if url in listed]
    issues=[];probes=0;started=time.monotonic()
    for d,url in candidates:
        if probes>=rule.get('max_probes',12) or time.monotonic()-started>120:break
        probes+=1
        try:
            data=fetch(url,hosts,rule.get('max_bytes',16*1024**2),opener,rule.get('not_found_title_pattern'))
            sha=validator(data,rule,d)
            if asset.get('expected_hash')==sha:
                issues.append('Publisher returned the installed file under a different edition URL')
                continue
            return {'status':'available','current_edition':label(current,period),'candidate':{'edition':label(d,period),'url':url,'sha256':sha,'bytes':len(data),'period_kind':rule.get('period_kind','publication_date')},'probes':probes,'issues':issues,'detail':'New '+label(d,period)+' edition available for review; saved '+label(current,period)+' edition retained.'}
        except MissingEdition:
            continue
        except HTTPError as error:
            if error.code in (404,410):continue
            issues.append('HTTP '+str(error.code))
            if error.code in (403,429):break
        except (OSError,ValueError,subprocess.SubprocessError) as error:issues.append(str(error)[:200])
    return {'status':'error' if issues else 'no_new_edition','current_edition':label(current,period),'candidate':None,'probes':probes,'issues':issues,'detail':'Edition discovery needs attention; installed copy retained.' if issues else 'No later verified edition found in the configured date window.'}
