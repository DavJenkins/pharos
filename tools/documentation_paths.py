"""Reject machine-local desktop paths in the portable public handbook."""
from pathlib import Path
import re

PATTERNS=(
    re.compile(r'(?<![A-Za-z0-9])[A-Za-z]:[\\/]'),
    re.compile(r'(?:[\\/])(?:Users|Documents and Settings)[\\/]',re.I),
)
TEXT_SUFFIXES={'.md','.html','.json','.yaml','.yml','.txt'}

def validate(paths,root=None):
    issues=[]
    for source in paths:
        source=Path(source)
        if not source.is_file() or source.suffix.lower() not in TEXT_SUFFIXES:continue
        for number,line in enumerate(source.read_text(encoding='utf-8-sig').splitlines(),1):
            if any(pattern.search(line) for pattern in PATTERNS):
                name=source.relative_to(root).as_posix() if root and source.is_relative_to(root) else source.name
                issues.append(f'{name}:{number}')
    if issues:
        raise ValueError('Public documentation contains desktop-specific absolute paths: '+', '.join(issues)+'. Use a chosen workspace-relative path or the applicable Ark service path.')
