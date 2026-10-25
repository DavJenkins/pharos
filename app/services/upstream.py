"""Explicit, bounded HTTP source checks. Never read or alter content payloads."""
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def source_urls(asset):
    return list(dict.fromkeys(asset[key] for key in ('download_url', 'mirror_url') if asset.get(key)))


def probe(address):
    # Some hosts reject HEAD. A Range GET fallback reads no body, even if ignored.
    for method in ('HEAD', 'GET'):
        request = Request(address, method=method, headers={
            'User-Agent': 'DataArk-SourceCheck/1.4', 'Range': 'bytes=0-0',
            'Accept-Encoding': 'identity'})
        try:
            with urlopen(request, timeout=10) as response:
                code = response.status
        except HTTPError as error:
            code = error.code
            error.close()
        except (OSError, URLError, ValueError):
            return {'url': address, 'status': 'unknown', 'reason': 'connection_failed'}
        if method == 'HEAD' and code in (405, 501):
            continue
        status = 'available' if 200 <= code < 300 else 'unavailable' if code in (404, 410) else 'unknown'
        return {'url': address, 'status': status, 'http_status': code}
    return {'url': address, 'status': 'unknown'}


def check_assets(assets, progress=None):
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    results = {}
    selected = [asset for asset in assets if source_urls(asset)]
    def one(asset):
        addresses = source_urls(asset)
        observations = [probe(address) for address in addresses]
        states = [result['status'] for result in observations]
        status = 'available' if 'available' in states else 'unavailable' if all(s == 'unavailable' for s in states) else 'unknown'
        return asset['id'], {'status': status, 'sources': addresses,
            'checked_at': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'observations': observations}
    if progress: progress(0, len(selected))
    with ThreadPoolExecutor(max_workers=4, thread_name_prefix='source-probe') as pool:
        for future in as_completed([pool.submit(one, asset) for asset in selected]):
            identifier, record = future.result()
            results[identifier] = record
            if progress: progress(len(results), len(selected))
    return {'version': 1, 'batch_started_at': started,
            'batch_finished_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'assets': results}


def read_batch(path):
    """Return validated sweep boundaries; legacy caches keep per-item times."""
    try:
        value = json.loads(Path(path).read_text(encoding='utf-8'))
        if value.get('version') != 1:
            return None
        start = datetime.fromisoformat(value['batch_started_at'])
        end = datetime.fromisoformat(value['batch_finished_at'])
        if start.tzinfo is not None and end.tzinfo is not None and start <= end:
            return start, end
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        pass
    return None


def read_state(path):
    try:
        value = json.loads(Path(path).read_text(encoding='utf-8'))
        if value.get('version') == 1 and isinstance(value.get('assets'), dict):
            return value['assets']
    except (OSError, ValueError, AttributeError):
        pass
    return {}


def asset_state(asset, state):
    record = state.get(asset['id'], {})
    # Never reuse a result for a different download URL or mirror.
    if not isinstance(record, dict) or record.get('sources') != source_urls(asset) or record.get('status') not in ('available', 'unavailable', 'unknown'):
        return {'status': 'unknown', 'checked_at': None}
    checked = record.get('checked_at')
    try:
        parsed = datetime.fromisoformat(checked)
        if parsed.tzinfo is None:
            raise ValueError('Missing timezone')
    except (TypeError, ValueError):
        return {'status': 'unknown', 'checked_at': None}
    return {'status': record['status'], 'checked_at': checked}
