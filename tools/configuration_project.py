#!/usr/bin/env python3
"""Split/check/compile public configuration; publication is explicit local-root work."""
import argparse
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app.services import configuration_project as project
from app.services.manifest import load_manifest,atomic_write


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['split','check','compile','publish'])
    parser.add_argument('--manifest',type=Path,default=ROOT/'dataark.yaml')
    parser.add_argument('--project',type=Path,default=ROOT/'config/library/ark.yaml')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--write',action='store_true')
    args=parser.parse_args()
    if args.action=='publish' and (not args.write or os.name!='posix' or os.geteuid()!=0 or ROOT.resolve()!=Path('/opt/dataark') or args.project.resolve()!=(ROOT/'config/library/ark.yaml').resolve()):raise ValueError('Publishing requires local root, the installed /opt/dataark project, and explicit --write. Compile and review first.')
    if args.action=='split':
        data=project.public(load_manifest(args.manifest));parts=project.split(data)
        assembled,_=project.assemble(parts.__getitem__)
        if assembled!=data:raise ValueError('Lossless split check failed.')
        print('Lossless split:',len(parts),'files;',len(data['repositories']),'collections;',len(data['assets']),'asset definitions.')
        print('ark.yaml:',len(parts['ark.yaml'].splitlines()),'lines,',len(parts['ark.yaml'].encode()),'bytes')
        if args.write:project.write(args.project.parent,data);print('Public project written:',args.project)
        else:print('Preview only. Add --write to create/update files; manual edits are never overwritten.')
        return
    data=project.public(load_manifest(args.project))
    if args.action=='check':
        expected=project.public(load_manifest(args.manifest))
        if data!=expected:raise ValueError('Project differs from the combined manifest. Compile and review the intended changes before publishing.')
        print('Project and combined manifest are exactly equivalent. No content or selections changed.');return
    if args.action=='compile':
        if not args.output:raise ValueError('Use --output with an explicit review file; this command does not publish.')
        if args.output.resolve() in (args.manifest.resolve(),(ROOT/'dataark.yaml').resolve()) or args.output.resolve().is_relative_to(args.project.parent.resolve()):raise ValueError('Compile to a separate review file, not over the manifest or project.')
        atomic_write(args.output,project.dump(data).encode());print('Public review snapshot:',args.output);return
    from app.services import configuration as editor
    raw,live=editor.current();text=editor.dump(data);editor.checked(text,live)
    result=editor.queue(text,editor.revision(raw),project_token=project.fingerprint(args.project.parent))
    print('Reviewed project queued:',result['id'])
    import subprocess
    subprocess.run(['systemctl','start','--no-block','dataark-configuration-publish.service'],check=True)


if __name__=='__main__':main()
