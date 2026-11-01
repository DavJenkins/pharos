"""Configured per-host certificate-chain additions; normal TLS checks stay enabled."""
import json
from pathlib import Path
import ssl
from urllib.parse import urlsplit


def extra_ca(url, root):
    policy = Path(root) / 'deploy/reference/source-tls.json'
    if not policy.exists():
        return None
    config = json.loads(policy.read_text(encoding='utf-8'))
    if config.get('schema') != 1:
        raise ValueError('Unsupported source TLS policy schema')
    entry = config.get('hosts', {}).get(urlsplit(url).hostname)
    if not entry:
        return None
    directory = (Path(root) / 'deploy/reference').resolve()
    name = entry['ca_bundle']
    if Path(name).is_absolute() or '\\' in name or '..' in Path(name).parts:
        raise ValueError('Unsafe configured certificate path')
    path = directory / name
    if path.is_symlink() or not path.resolve().is_relative_to(directory) or path.suffix.lower() not in {'.pem','.crt'}:
        raise ValueError('Certificate bundle must be a local reference certificate')
    if not path.is_file():
        raise ValueError('Configured certificate-chain file is missing')
    return path


def context(url, root):
    value = ssl.create_default_context()
    certificate = extra_ca(url, root)
    if certificate:
        value.load_verify_locations(cafile=str(certificate))
    return value
