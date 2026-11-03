"""Software updates in the durable lifecycle feed already consumed by HA."""
from pathlib import Path


def _emit(kind, **fields):
    try:
        if Path(__file__).parent == Path('/usr/local/libexec'):
            # The privileged updater imports only its root-owned installed copy.
            import software_collection_events as feed
        else:
            from app.services import collection_changes as feed
        feed.safe_record(kind, action='software_update', collection_id='ark-software', **fields)
    except Exception:
        # Notification availability must never affect an update or rollback.
        import logging
        logging.getLogger(__name__).warning('Software update notification could not be recorded')


def available(result):
    channel=result.get('channel','stable');release=result.get('release') or {}
    if result.get('state')=='unavailable':return  # Retain the last known result while offline.
    pending=result.get('installation_supported') and result.get('state')=='newer_release'
    _emit('suggested' if pending else 'idle',
          title='Ark software update '+release.get('tag','')+' available' if pending else '',
          operation_id=release.get('tag','') if pending else '',
          activity_key='software_updates:'+channel)


def transaction(journal):
    state=journal.get('state');release=journal.get('release','')
    kind={'preparing':'request_started','completed':'installed','rolled_back':'failed','refused':'failed','interrupted_before_apply':'failed'}.get(state)
    if not kind:return
    wording={'preparing':'Installing','completed':'Applied','rolled_back':'Rolled back','refused':'Refused','interrupted_before_apply':'Interrupted'}[state]
    versions=' ('+str(journal['from_revision'])[:12]+' → '+str(journal['to_revision'])[:12]+')' if journal.get('from_revision') and journal.get('to_revision') else ''
    _emit(kind,title=wording+' Ark software '+release+versions,operation_id=journal.get('id',''),
          error_type=state if kind=='failed' else '',activity_key='software_installation')


def content(asset, result):
    """A verified publisher change is pending review, never silently an installation."""
    if result.get('status')=='error':return
    import hashlib,json
    discovery=result.get('edition_discovery') or {}
    candidate=discovery.get('candidate') if discovery.get('status')=='available' else None
    pending=bool(result.get('pending_change') or candidate)
    marker=hashlib.sha256(json.dumps([result.get('fingerprint'),candidate],sort_keys=True).encode()).hexdigest()
    edition=' ('+str(candidate.get('edition'))+')' if candidate else ''
    try:
        from app.services.collection_changes import safe_record
        safe_record('suggested' if pending else 'idle',action='content_update',collection_id=asset['id'],
                    title='Content update available: '+asset['title']+edition if pending else '',
                    operation_id=marker if pending else '',activity_key='content_update:'+asset['id'])
    except Exception:
        import logging
        logging.getLogger(__name__).warning('Content update notification could not be recorded')


def download(value):
    """Expose download/verification progress without installing or flooding events."""
    kind={'queued':'queued','downloading':'downloading','verifying':'verifying','verified':'suggested',
          'failed':'failed','interrupted':'failed'}.get(value.get('state'))
    if kind:
        _emit(kind,title='Ark software '+str(value.get('tag',''))+': '+str(value.get('state','')),
              operation_id=value.get('id',''),activity_key='software_download',percent=value.get('percent'),
              error_type=value.get('state') if kind=='failed' else '')
