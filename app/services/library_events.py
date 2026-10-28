"""Library diagnostics in the existing Ark event stream; never log request bodies."""
from contextvars import ContextVar
from functools import wraps
from pathlib import Path
import time
import uuid
from app.core import events

DEBUG_FLAG=Path('/var/lib/ark/debug_status')
current=ContextVar('library_operation',default=None)
FIELDS={'action','asset_id','title','phase','elapsed_seconds','bytes_freed','bytes_requested','error_type','reason','outcome','operation','percent'}

def emit(event, detailed=False, **fields):
    from app.services.collection_changes import from_library
    from_library(event, {**fields, 'operation':fields.get('operation') or current.get()})
    if detailed and not DEBUG_FLAG.exists():
        return
    clean={k:(v[:400] if isinstance(v,str) else v) for k,v in fields.items()
        if k in FIELDS and isinstance(v,(str,int,float,bool,type(None)))}
    operation=current.get()
    if operation:
        clean.setdefault('operation',operation)
    try:
        events.info('library_'+event,source='library',**clean)
    except OSError:
        # A logging failure must not interrupt content recovery or deletion cleanup.
        pass

def phase(name,**fields):
    emit('stage',detailed=True,phase=name,**fields)

def tracked(action):
    def decorate(function):
        @wraps(function)
        def run(payload):
            token=current.set(uuid.uuid4().hex)
            started=time.monotonic()
            identity={}
            try:
                from app.services.library import ROOT
                from app.services.manifest import load_manifest
                data=load_manifest(ROOT/'dataark.yaml')
                if isinstance(payload,dict):
                    asset=next((a for a in data['assets'] if a['id']==payload.get('asset_id')),None)
                    repo=next((r for r in data['repositories'] if r['id']==payload.get('repository_id')),None)
                    if asset:
                        identity={'asset_id':asset['id'],'title':asset['title']}
                    elif repo:
                        identity={'title':repo['title']}
            except (OSError,ValueError,KeyError,TypeError):
                pass
            emit('operation_started',action=action,**identity)
            try:
                result=function(payload)
                fields={'action':action,'elapsed_seconds':round(time.monotonic()-started,2),**identity}
                if action=='remove' and isinstance(payload,dict) and type(payload.get('bytes')) is int:
                    fields['bytes_freed']=payload['bytes']
                if action=='download' and isinstance(payload,dict) and type(payload.get('bytes')) is int:
                    fields['bytes_requested']=payload['bytes']
                emit('operation_completed',outcome='removed' if action=='remove' else 'queued',**fields)
                return result
            except Exception as error:
                emit('operation_failed',action=action,error_type=type(error).__name__,reason=str(error),elapsed_seconds=round(time.monotonic()-started,2),**identity)
                raise
            finally:
                current.reset(token)
        return run
    return decorate
