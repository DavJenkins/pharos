"""Vehicle document metadata is authored in the catalogue, never inferred legal prose."""
import copy
import html
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

FIELDS = ('publisher', 'document_kind', 'scope', 'applicability', 'rights_notice')


def load(path):
    value = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(value, dict) or value.get('schema') != 1:
        raise ValueError('Vehicle catalogue needs schema: 1, repository, defaults and documents.')
    if not isinstance(value.get('repository'), dict) or not isinstance(value.get('documents'), list):
        raise ValueError('Vehicle catalogue needs repository metadata and a document list.')
    defaults = value.get('defaults', {})
    seen = set(); documents = []
    for original in value['documents']:
        item = copy.deepcopy(defaults) | copy.deepcopy(original)
        if not isinstance(item.get('id'), str) or not re.fullmatch('[a-z0-9][a-z0-9-]*', item['id']) or item['id'] in seen:
            raise ValueError('Vehicle document IDs must be unique lowercase slugs.')
        seen.add(item['id'])
        for field in ('title', 'model', *FIELDS):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise ValueError('Vehicle document needs explicit '+field+': '+item['id'])
        if type(item.get('year')) is not int or not 1886 <= item['year'] <= 2200:
            raise ValueError('Vehicle document needs an explicit model year.')
        url = urlsplit(item.get('url', ''))
        if url.scheme != 'https' or not url.hostname or url.username or url.password:
            raise ValueError('Vehicle documents require a public HTTPS source URL.')
        required = item.get('validation_text', [])
        if not isinstance(required, list) or any(not isinstance(t, str) or not t.strip() for t in required):
            raise ValueError('validation_text must be a list of explicit text fragments.')
        documents.append(item)
    return value | {'documents': documents}


def validate_document(item, text):
    normalized = ' '.join(text.casefold().split())
    required = [str(item['year']), item['model'], *item.get('validation_text', [])]
    if any(' '.join(t.casefold().split()) not in normalized for t in required):
        raise ValueError('Configured vehicle/document identity did not match PDF: '+item['id'])


def source_note(item):
    return ' '.join(item[field].strip() for field in FIELDS if item.get(field))


def render_index(records):
    """Render only supplied source statements, plus measured provenance."""
    out = ['<h1>Vehicle documents</h1><p>Sources, document scope, applicability and publisher notices.</p>']
    labels = {'publisher': 'Publisher', 'document_kind': 'Document type', 'scope': 'Scope',
              'applicability': 'Applicability', 'rights_notice': 'Publisher notice',
              'retrieved_at': 'Retrieved', 'sha256': 'Verified file SHA-256'}
    for item in records:
        out.append('<section><h2>'+html.escape(item['title'])+'</h2><p><a href="/library-files/'+html.escape(item['path'], quote=True)+'">Open document</a> · <a href="'+html.escape(item['url'], quote=True)+'">Publisher source ↗</a></p><dl>')
        for key, label in labels.items():
            if item.get(key):out.append('<dt><strong>'+label+'</strong></dt><dd>'+html.escape(str(item[key]))+'</dd>')
        out.append('</dl></section>')
    return ''.join(out)
