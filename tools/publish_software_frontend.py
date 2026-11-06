#!/opt/dataark/venv/bin/python
"""Regenerate the dashboard from the recipient's existing configuration, as admin."""
from pathlib import Path
import sys
ROOT=Path('/opt/dataark')
sys.path.insert(0,str(ROOT))
from app.services.manifest import build,load_manifest

def main():
    project=ROOT/'dataark.yaml'
    if not project.is_file():project=ROOT/'config/library/ark.yaml'
    config=load_manifest(project);mount=Path(config['system']['base_mount'])
    if not mount.is_mount():raise ValueError('Content storage must be mounted before dashboard publication')
    for output in (ROOT/'app/static/index.html',Path('/var/www/html/index.html')):
        build(project,ROOT/'app/templates/index.html',output)

if __name__=='__main__':main()
