"""Shared, offline DEJ presentation for the handbook and interactive API docs."""
import html

def masthead(section, active):
    links = [('dashboard', '/', 'Dashboard'), ('help', '/docs/SUMMARY.html', 'Help'), ('api', '/api/docs', 'Developer API')]
    navigation = ''.join('<a href="' + url + '"' + (' aria-current="page"' if key == active else '') + '>' + title + '</a>' for key, url, title in links)
    return '<header class="docs-masthead"><a class="docs-brand" href="/"><span class="docs-maker">DEJ SOFTWARE</span><strong>Data Ark</strong></a><div class="docs-masthead-right"><p>' + html.escape(section) + '</p><nav aria-label="Documentation navigation">' + navigation + '</nav></div></header>'

def footer():
    return '<footer class="docs-footer"><span>DEJ Software</span><span>Practical software for real life.</span></footer>'
