#!/usr/bin/env python3

from pathlib import Path
import shutil
import html
import re
from urllib.parse import urlsplit, urlunsplit

SOURCE = Path("/opt/dataark/docs")
TARGET = Path("/tmp/dataark-docs")


###############################################################################
# Start with a completely clean output directory
###############################################################################

if TARGET.exists():
    shutil.rmtree(TARGET)

TARGET.mkdir(parents=True)


def inline_html(text):
    def link(match):
        label, target = match.groups()
        parts = urlsplit(target)
        if parts.scheme not in ("", "http", "https", "mailto"):
            return html.escape(match.group(0))
        if not parts.scheme and not parts.netloc and parts.path.endswith(".md"):
            target = urlunsplit(parts._replace(path=parts.path[:-3] + ".html"))
        return f'<a href="{html.escape(target, quote=True)}">{html.escape(label)}</a>'

    chunks = []
    start = 0
    for match in re.finditer(r"\[([^\]]+)\]\(([^\s)]+)\)", text):
        chunks.append(html.escape(text[start:match.start()]))
        chunks.append(link(match))
        start = match.end()
    chunks.append(html.escape(text[start:]))
    return "".join(chunks)


def markdown_to_html(text):

    out = []

    out.append("""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Data Ark Documentation</title>

<style>

body{
    max-width:900px;
    margin:40px auto;
    font-family:Arial,Helvetica,sans-serif;
    background:#202124;
    color:#e8e8e8;
    line-height:1.6;
}

h1,h2,h3{
    color:#7fc8ff;
}

pre{
    background:#111;
    padding:1em;
    overflow:auto;
}

code{
    font-family:Consolas,monospace;
}

a{
    color:#7fc8ff;
}

</style>

</head>
<body>
""")

    in_list = False

    for line in text.splitlines():

        if line.startswith("# "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h1>{inline_html(line[2:])}</h1>")
            continue

        if line.startswith("## "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h2>{inline_html(line[3:])}</h2>")
            continue

        if line.startswith("### "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h3>{inline_html(line[4:])}</h3>")
            continue

        if line.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{inline_html(line[2:])}</li>")
            continue

        if in_list:
            out.append("</ul>")
            in_list = False

        if line.strip():
            out.append(f"<p>{inline_html(line)}</p>")

    if in_list:
        out.append("</ul>")

    out.append("</body></html>")

    return "\n".join(out)


for md in SOURCE.rglob("*.md"):

    rel = md.relative_to(SOURCE)
    outfile = TARGET / rel.with_suffix(".html")

    outfile.parent.mkdir(parents=True, exist_ok=True)

    outfile.write_text(
        markdown_to_html(md.read_text(encoding="utf-8")),
        encoding="utf-8",
    )

print("Published", len(list(SOURCE.rglob("*.md"))), "documents.")
