"""Download official releases as the web user; reuse the signed root verifier."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import threading
import time
import uuid
from urllib.parse import urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener

from app.services import software_installation as installation
from app.services import software_updates as releases

MAX_BYTES = 256 * 1024**2
ACTIVE = {'queued', 'downloading', 'verifying'}
GUARD = threading.RLock()


class DownloadError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message); self.status = status


def paths():
    return installation.INBOX/'download-status.json', installation.INBOX/'download.lock'


def save(value):
    with GUARD:
        path, _ = paths()
        value = {**value, 'updated_at': time.time()}
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temp = Path(stream.name)
            stream.write(json.dumps(value).encode())
        try:
            temp.chmod(0o600); os.replace(temp, path)
        finally: temp.unlink(missing_ok=True)
    try:
        from tools.update_notifications import download
        download(value)
    except Exception:pass  # Telemetry must never decide whether a package is valid.
    return value


def read():
    try:
        value = json.loads(paths()[0].read_text())
        if not isinstance(value, dict): raise ValueError()
        return value
    except FileNotFoundError: return {'state': 'idle'}
    except (OSError, ValueError): return {'state':'unavailable', 'message':'Download status is unavailable.'}


def status():
    import fcntl
    with GUARD:
        value = read()
        if value.get('state') not in ACTIVE: return value
        try:
            with paths()[1].open('a') as lock:
                try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError: return value
                # A process restart cannot turn a partial download into a
                # verified package. The caretaker may retry explicitly.
                value = save({**value, 'state':'interrupted', 'message':'Download interrupted. Retry downloading; running software was not changed.'})
                identifier = value.get('id','')
                if re.fullmatch(r'[0-9a-f]{32}',identifier):
                    (installation.INBOX/(identifier+'.tar.gz')).unlink(missing_ok=True)
                return value
        except OSError: return {'state':'unavailable','message':'Download storage is unavailable.'}


def validate_url(url):
    value = urlsplit(url)
    if value.scheme != 'https' or value.hostname not in {'github.com','release-assets.githubusercontent.com','objects.githubusercontent.com'} or value.username or value.password or value.port not in (None,443):
        raise DownloadError('Software download left the official HTTPS release hosts.')


class OfficialRedirect(HTTPRedirectHandler):
    max_redirections = 5
    def redirect_request(self, request, fp, code, message, headers, newurl):
        validate_url(newurl)
        return super().redirect_request(request,fp,code,message,headers,newurl)


def package(tag, preview):
    choices = releases.candidates(releases.read_releases(), preview)
    item = next((item for item in choices if item['tag_name'] == tag), None)
    if not item: raise DownloadError('This release is no longer available in the selected channel. Check for updates again.')
    name = 'data-ark-'+tag+'.tar.gz'
    matches = [a for a in item['assets'] if a.get('name') == name and a.get('state') == 'uploaded']
    if len(matches) != 1: raise DownloadError('Release must contain exactly one software package.')
    asset = matches[0]; size = asset.get('size')
    if type(size) is not int or not 0 < size <= MAX_BYTES: raise DownloadError('Release package is empty or exceeds 256 MiB.')
    digest = asset.get('digest')
    if digest and not re.fullmatch(r'sha256:[0-9a-f]{64}',digest): raise DownloadError('Unsupported release package checksum.')
    url = 'https://github.com/DavJenkins/pharos/releases/download/'+tag+'/'+name
    if asset.get('browser_download_url') != url: raise DownloadError('Release package URL does not match the official repository.')
    relation = releases.relationship(releases.installed().get('revision'), item.get('target_commitish'))
    if relation in {'same','development_ahead'}: raise DownloadError('This Ark already contains this release. Check for a newer release.')
    return url, size, digest.removeprefix('sha256:') if digest else None


def run(job, lock, opener=None):
    path = installation.INBOX/(job['id']+'.tar.gz')
    try:
        url, total, expected = package(job['tag'], job['preview'])
        if shutil.disk_usage(installation.INBOX).free < total + 64*1024**2: raise DownloadError('Not enough system-disk space for this download.')
        validate_url(url)
        job = save({**job,'state':'downloading','total_bytes':total,'downloaded_bytes':0,'percent':0,'message':'Downloading signed software package…'})
        digest = hashlib.sha256(); downloaded = 0; started = time.monotonic(); last = started
        opener = opener or build_opener(OfficialRedirect()).open
        with opener(Request(url,headers={'User-Agent':'Pharos-Data-Ark-update/1','Accept-Encoding':'identity'}),timeout=15) as response:
            validate_url(response.url)
            length = response.headers.get('Content-Length')
            if length and int(length) != total: raise DownloadError('Downloaded package length does not match the release.')
            with path.open('xb') as stream:
                path.chmod(0o600)
                while True:
                    if time.monotonic()-started > 900: raise DownloadError('Download timed out. Retry when the connection is available.')
                    chunk = response.read(min(256*1024, total-downloaded+1))
                    if not chunk: break
                    downloaded += len(chunk)
                    if downloaded > total or downloaded > MAX_BYTES: raise DownloadError('Software download exceeds the declared size.')
                    stream.write(chunk); digest.update(chunk)
                    if time.monotonic()-last >= .5:
                        job=save({**job,'downloaded_bytes':downloaded,'percent':int(downloaded*100/total)}); last=time.monotonic()
        if downloaded != total: raise DownloadError('Software download was incomplete. Retry downloading.')
        if expected and digest.hexdigest() != expected: raise DownloadError('Release package checksum did not match. Nothing installed.')
        job=save({**job,'state':'verifying','downloaded_bytes':downloaded,'percent':100,'message':'Download complete. Verifying signature and compatibility…'})
        staged=installation.invoke({'action':'stage','id':job['id']})
        if not staged.get('ok'): raise DownloadError(staged.get('error','Signed package verification failed.'))
        if staged.get('release') != job['tag']: raise DownloadError('Signed package release does not match the selected release. Nothing installed.')
        save({**job,'state':'verified','staged':staged,'message':'Signature and compatibility verified. Review the package, then install it.'})
    except Exception as error:
        message = str(error) if isinstance(error, DownloadError) else 'Download could not complete. Check the Ark’s internet connection and retry; running software was not changed.'
        save({**job,'state':'failed','message':message[:500]})
    finally:
        try: path.unlink(missing_ok=True)
        finally: lock.close()


def start(tag, preview=False):
    import fcntl
    if not isinstance(tag,str) or not releases.TAG.fullmatch(tag) or not tag.startswith('software-') or type(preview) is not bool:
        raise DownloadError('Select a published software release; bootstrap kits are not updates.')
    if '-preview.' in tag and not preview: raise DownloadError('Preview releases require explicit opt-in.')
    with GUARD:
        current=installation.status()
        if not current.get('configured'): raise DownloadError('The signed software updater is not configured.',503)
        if current.get('state') in {'queued','preparing','applying','checking','rolling_back','rollback_pending_health'}:
            raise DownloadError('An installation or recovery is already running.',409)
        try: lock=paths()[1].open('a')
        except OSError: raise DownloadError('Software download storage is unavailable.',503) from None
        try:
            try: fcntl.flock(lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError: raise DownloadError('A software download is already running.',409) from None
            job=save({'id':uuid.uuid4().hex,'tag':tag,'preview':preview,'state':'queued','started_at':time.time(),'message':'Looking up the official software package…'})
            threading.Thread(target=run,args=(job,lock),daemon=True,name='software-release-download').start()
            return job
        except BaseException:
            lock.close(); raise
