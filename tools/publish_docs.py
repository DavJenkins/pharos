#!/usr/bin/env python3

from pathlib import Path
import html

SOURCE = Path("/opt/dataark/docs")
TARGET = Path("/tmp/dataark-docs")


def markdown_to_html(text):

    lines = text.splitlines()

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
h1,h2,h3{color:#7fc8ff;}
pre{background:#111;padding:1em;overflow:auto;}
code{font-family:Consolas,monospace;}
a{color:#7fc8ff;}
</style>

</head>
<body>
""")

    in_list = False

    for line in lines:

        if line.startswith("# "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h1>{html.escape(line[2:])}</h1>")
            continue

        if line.startswith("## "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h2>{html.escape(line[3:])}</h2>")
            continue

        if line.startswith("### "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h3>{html.escape(line[4:])}</h3>")
            continue

        if line.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{html.escape(line[2:])}</li>")
            continue

        if in_list:
            out.append("</ul>")
            in_list = False

        if line.strip():
            out.append(f"<p>{html.escape(line)}</p>")

    if in_list:
        out.append("</ul>")

    out.append("</body></html>")

    return "\n".join(out)


TARGET.mkdir(parents=True, exist_ok=True)

for md in SOURCE.rglob("*.md"):

    rel = md.relative_to(SOURCE)

    outfile = TARGET / rel.with_suffix(".html")

    outfile.parent.mkdir(parents=True, exist_ok=True)

    outfile.write_text(
        markdown_to_html(md.read_text(encoding="utf-8")),
        encoding="utf-8"
    )

print("Published to", TARGET)
