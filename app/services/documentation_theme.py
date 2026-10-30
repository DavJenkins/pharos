"""Shared, offline DEJ presentation for the handbook and interactive API docs."""
import html,hashlib
from pathlib import Path

def stylesheet_url():
    css=Path(__file__).resolve().parents[1]/"static/assets/css/ark-documentation.css"
    return "/assets/css/ark-documentation.css?v="+hashlib.sha256(css.read_bytes()).hexdigest()[:16]


def masthead(section, active):
    links = [('dashboard', '/', 'Dashboard'), ('help', '/docs/SUMMARY.html', 'Help'), ('api', '/api/docs', 'Developer API')]
    navigation = ''.join('<a href="' + url + '"' + (' aria-current="page"' if key == active else '') + '>' + title + '</a>' for key, url, title in links)
    return '<header class="docs-masthead"><div class="docs-brand"><a class="docs-maker" href="https://www.dejsoftware.com/" title="DEJ Software website (internet required)"><img src="/assets/dej-software-footer.webp" width="1024" height="192" alt="DEJ Software™"></a><a class="docs-home" href="/"><strong>Data Ark</strong></a></div><div class="docs-masthead-right"><p>' + html.escape(section) + '</p><nav aria-label="Documentation navigation">' + navigation + '</nav></div></header>'

def footer():
    return '<footer class="docs-footer"><a class="docs-footer-brand" href="https://www.dejsoftware.com/" title="DEJ Software website (internet required)"><img src="/assets/dej-software-footer.webp" width="1024" height="192" alt="DEJ Software™ — Practical Software for Real Life"></a></footer><script src="/assets/js/background-sign-link.js?v=brand-links-2"></script>'
