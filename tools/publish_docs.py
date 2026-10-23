#!/usr/bin/env python3

from pathlib import Path
import argparse
import tempfile
import html
import re
from urllib.parse import urlsplit, urlunsplit

SOURCE = Path(__file__).resolve().parents[1] / 'docs'


def escaped_inline(text):
    parts = re.split(r"(`[^`]+`)", text)
    return "".join("<code>" + html.escape(part[1:-1]) + "</code>" if part.startswith("`") and part.endswith("`") else html.escape(part) for part in parts)


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
        chunks.append(escaped_inline(text[start:match.start()]))
        chunks.append(link(match))
        start = match.end()
    chunks.append(escaped_inline(text[start:]))
    return "".join(chunks)


def markdown_to_html(text):

    out = []

    out.append("""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Data Ark Documentation</title>

<style>

body{
    max-width:900px;
    margin:40px auto;
    padding:0 1rem;
    overflow-wrap:anywhere;
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
    in_code = False

    for line in text.splitlines():
        if line.startswith("```"):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append("</code></pre>" if in_code else "<pre><code>")
            in_code = not in_code
            continue
        if in_code:
            out.append(html.escape(line))
            continue

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

    if in_code:
        out.append("</code></pre>")
    out.append("</body></html>")

    return "\n".join(out)



def publish(source, target):
    source, target = Path(source), Path(target)
    if not source.is_dir():
        raise ValueError('Documentation source directory is missing')
    # Never remove or overwrite a directory left by another user or deployment.
    if target.is_symlink() or (target.exists() and (not target.is_dir() or any(target.iterdir()))):
        raise ValueError('Documentation output must be a new or empty directory')
    documents = sorted(source.rglob('*.md'))
    if not documents:
        raise ValueError('No documentation source files found')
    target.mkdir(parents=True, exist_ok=True)
    for md in documents:
        outfile = target / md.relative_to(source).with_suffix('.html')
        outfile.parent.mkdir(parents=True, exist_ok=True)
        outfile.write_text(markdown_to_html(md.read_text(encoding='utf-8')), encoding='utf-8')
    return len(documents)


def main():
    parser = argparse.ArgumentParser(description='Publish documentation into a fresh directory.')
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--output', type=Path, help='New or empty output directory; defaults to a unique temporary directory.')
    args = parser.parse_args()
    target = args.output if args.output is not None else Path(tempfile.mkdtemp(prefix='dataark-docs-'))
    try:
        count = publish(args.source, target)
    except (OSError, ValueError) as error:
        parser.exit(1, 'Documentation publishing failed: ' + str(error) + '\n')
    print('Published', count, 'documents to', str(target))


if __name__ == '__main__':
    main()
