"""Shared, offline DEJ presentation for the handbook and interactive API docs."""
import html,hashlib
from pathlib import Path

def stylesheet_url():
    css=Path(__file__).resolve().parents[1]/"static/assets/css/ark-documentation.css"
    return "/assets/css/ark-documentation.css?v="+hashlib.sha256(css.read_bytes()).hexdigest()[:16]


def masthead(section, active):
    links = [('dashboard', '/', 'Dashboard'), ('help', '/docs/summary.html', 'Help'), ('api', '/api/docs', 'Developer API')]
    navigation = ''.join('<a href="' + url + '"' + (' aria-current="page"' if key == active else '') + '>' + title + '</a>' for key, url, title in links)
    return '<header class="docs-masthead"><div class="docs-brand"><a class="docs-maker" href="https://www.dejsoftware.com/" title="DEJ Software website (internet required)"><img src="/assets/dej-software-footer.webp" width="1024" height="192" alt="DEJ Software™"></a><a class="docs-home" href="/"><strong>Data Ark</strong></a></div><div class="docs-masthead-right"><p>' + html.escape(section) + '</p><nav aria-label="Documentation navigation">' + navigation + '</nav></div></header>'

def footer():
    return '<footer class="docs-footer"><a class="docs-footer-brand" href="https://www.dejsoftware.com/" title="DEJ Software website (internet required)"><img src="/assets/dej-software-footer.webp" width="1024" height="192" alt="DEJ Software™ — Practical Software for Real Life"></a></footer><script src="/assets/js/dej-community-links.js?v=1"></script><script src="/assets/js/background-sign-link.js?v=brand-links-2"></script>'


def online_notice(url, publication_date=None):
    """An optional visible counterpart link; no external reading dependency."""
    date = (' · Published ' + html.escape(publication_date)) if publication_date else ''
    return '<p class="docs-online-version" style="font-size:.85em;margin-top:1.5em"><a href="' + html.escape(url, quote=True) + '" target="_blank" rel="noopener noreferrer">Online version ↗</a> <span>· Internet required' + date + '</span></p>'


def online_guide_url(relative, base='https://www.dejsoftware.com'):
    from urllib.parse import quote
    name=Path(relative).with_suffix('.html').as_posix()
    if name=='summary.html':return base.rstrip('/')+'/data-ark/docs/'
    if name=='index.html':name='overview.html'
    return base.rstrip('/')+'/data-ark/docs/'+quote(name,safe='/')
