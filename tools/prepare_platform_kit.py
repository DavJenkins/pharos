#!/usr/bin/env python3
"""Build a public configuration/software archive for an explicit platform profile."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))


def main():
    from deploy.bootstrap_platform import profile
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',required=True)
    parser.add_argument('--output',type=Path,default=Path('/var/lib/dataark/platform-kits'))
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args();spec=profile(args.profile)
    print(json.dumps({'profile':spec['id'],'processor':spec['baseline']['architecture'],
                      'network':spec['network_mode'],'output':str(args.output),
                      'contents':'Public configuration, source and architecture-matched tools; no library payloads, credentials or device identities.',
                      'tool_download_may_be_needed':True,'acceptance':spec['acceptance']},indent=2))
    if not args.apply:print('Preview only. Add --apply to build this archive.');return
    if os.geteuid()!=0:raise SystemExit('Use sudo to read and export the installed public configuration.')
    from tools.content_profile import export,read
    from tools.replicate_drive import kit_files
    from tools.build_bootstrap_release import inspect_config
    args.output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='platform-kit-',dir=args.output) as tmp:
        stage=Path(tmp);recipe=stage/'recipe';drive=stage/'drive';drive.mkdir()
        export(recipe);manifest=read(recipe/read(recipe/'content.yaml')['manifest']);inspect_config(manifest)
        metadata=kit_files(drive,profile=recipe/'content.yaml',platform_profile=args.profile)
        config_hash=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()[:12]
        name='data-ark-kit-'+args.profile+'-'+metadata['source_revision'][:12]+'-'+config_hash+'.tar.gz'
        target=args.output/name
        if target.exists():raise ValueError('An archive for this source/configuration already exists; it was not overwritten.')
        partial=stage/name
        with tarfile.open(partial,'w:gz') as archive:
            for path in sorted(drive.iterdir()):archive.add(path,arcname=path.name)
        digest=hashlib.sha256(partial.read_bytes()).hexdigest();partial.replace(target)
        target.with_suffix(target.suffix+'.sha256').write_text(digest+'  '+target.name+'\n')
        print(json.dumps({'archive':str(target),'bytes':target.stat().st_size,'sha256':digest,'profile':spec['id']},indent=2))


if __name__=='__main__':main()
