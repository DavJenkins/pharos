#!/usr/bin/env python3

from pathlib import Path
import argparse
import tempfile
import html
import re
import sys
import shutil
from urllib.parse import urlsplit, urlunsplit

SOURCE = Path(__file__).resolve().parents[1] / 'docs'
sys.path.insert(0, str(SOURCE.parent))
from app.services.documentation_theme import masthead, footer, stylesheet_url
from tools.documentation_paths import validate as validate_public_paths



CODE_CONTROLS = r'''<style>
.command-block{position:relative;margin:1.2rem 0;padding:1rem;border:1px solid #54718a;border-radius:.5rem;background:#0b1c30;color:#f4e8c6}
.command-block pre{margin:0 0 .8rem!important;padding:.3rem!important;background:transparent!important;color:inherit!important;overflow:auto;white-space:pre!important;text-align:left}
.command-block code{background:transparent!important;color:inherit!important;font-family:Consolas,monospace}
.command-block .copy-command{min-height:44px;padding:.4rem .9rem;border:1px solid #c5a253;border-radius:.35rem;background:#f3e7c8;color:#142c43;cursor:pointer;font:inherit}
.copy-feedback{margin-left:.7rem;font-size:.9rem}
</style><script>
document.addEventListener('click',async function(event){
 const button=event.target.closest('.copy-command');if(!button)return;
 const block=button.closest('.command-block'),text=block.querySelector('code').textContent.replace(/^\n|\n$/g,''),feedback=block.querySelector('.copy-feedback');
 try{
  if(window.isSecureContext&&navigator.clipboard){await navigator.clipboard.writeText(text);}
  else{const field=document.createElement('textarea');field.value=text;field.style.position='fixed';field.style.opacity='0';document.body.appendChild(field);field.select();let copied=false;try{copied=document.execCommand('copy');}finally{field.remove();button.focus();}if(!copied)throw new Error('Clipboard unavailable');}
  feedback.textContent='Copied';
 }catch(error){feedback.textContent='Select the code and copy it manually.';}
});
</script>'''

def escaped_inline(text):
    parts = re.split(r"(`[^`]+`)", text)
    def formatted(part):
        value=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',html.escape(part))
        return re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)',r'<em>\1</em>',value)
    return "".join("<code>" + html.escape(part[1:-1]) + "</code>" if part.startswith("`") and part.endswith("`") else formatted(part) for part in parts)


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
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Data Ark Documentation</title>

<link rel="stylesheet" href="/assets/css/ark-documentation.css?v=1">

</head>
<body class="ark-documentation"><div class="documentation-shell">
""")
    out[0]=out[0].replace("/assets/css/ark-documentation.css?v=1",stylesheet_url())
    out.append(masthead('HELP & HANDBOOK', 'help'))
    out.append('<main class="docs-paper handbook-paper"><p class="docs-eyebrow">THE DATA ARK HANDBOOK</p>')

    in_list = False
    in_code = False
    has_code = False

    for line in text.splitlines():
        if line.startswith("```"):
            if in_list:
                out.append("</ul>")
                in_list = False
            has_code = True
            out.append('</code></pre><button type="button" class="copy-command">Copy code</button><span class="copy-feedback" role="status"></span></div>' if in_code else '<div class="command-block"><pre><code>')
            in_code = not in_code
            continue
        if in_code:
            out.append(html.escape(line))
            continue

        screenshot = re.fullmatch(r'!\[([^\]]*)\]\(([^\s)]+)\)\s*',line)
        if screenshot:
            if in_list:out.append('</ul>');in_list=False
            caption,target=screenshot.groups();url=urlsplit(target)
            if url.scheme or url.netloc or Path(url.path).suffix.lower() not in {'.png','.jpg','.jpeg','.webp'}:
                raise ValueError('Help screenshots must use local image files')
            escaped=html.escape(target,quote=True);alt=html.escape(caption,quote=True)
            out.append('<figure class="help-screenshot" style="margin:1.4rem 0"><a href="'+escaped+'" aria-label="Open full-size screenshot: '+alt+'"><img src="'+escaped+'" alt="'+alt+'" loading="lazy" style="display:block;width:auto;max-width:100%;height:auto;max-height:680px;border:1px solid #8ea6b8;border-radius:8px"></a><figcaption style="font-size:.9rem;line-height:1.5;margin-top:.5rem">'+html.escape(caption)+' Select the image to enlarge it.</figcaption></figure>')
            continue

        if line.startswith('::: details '):
            if in_list:
                out.append('</ul>'); in_list = False
            out.append('<details class="content-details"><summary>' + inline_html(line[len('::: details '):]) + '</summary>')
            continue
        if line.strip() == ':::':
            if in_list:
                out.append('</ul>'); in_list = False
            out.append('</details>')
            continue

        if line.strip() == '---':
            if in_list:
                out.append('</ul>'); in_list = False
            out.append('<hr>')
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
            anchor = re.sub(r'[^a-z0-9]+', '-', line[3:].lower()).strip('-')
            out.append(f'<h2 id="{anchor}">{inline_html(line[3:])}</h2>')
            continue

        if line.startswith("### "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h3>{inline_html(line[4:])}</h3>")
            continue

        if line.startswith(("- ", "* ", "+ ")):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{inline_html(line[2:])}</li>")
            continue

        if not line.strip():
            continue
        if in_list:
            out.append("</ul>")
            in_list = False

        if line.strip():
            out.append(f"<p>{inline_html(line)}</p>")

    if in_list:
        out.append("</ul>")

    if in_code:
        out.append('</code></pre><button type="button" class="copy-command">Copy code</button><span class="copy-feedback" role="status"></span></div>')
    if has_code:
        out.append(CODE_CONTROLS)
    out.append('</main>' + footer() + '</div></body></html>')

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
    validate_public_paths(source.rglob('*'),source)
    target.mkdir(parents=True, exist_ok=True)
    for md in documents:
        outfile = target / md.relative_to(source).with_suffix('.html')
        outfile.parent.mkdir(parents=True, exist_ok=True)
        outfile.write_text(markdown_to_html(md.read_text(encoding='utf-8')), encoding='utf-8')
    for asset in source.rglob('*'):
        if asset.is_file() and asset.suffix in {'.json','.yaml','.yml','.txt','.pdf','.png','.jpg','.jpeg','.svg','.webp','.css'}:
            destination=target/asset.relative_to(source);destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(asset,destination)
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
