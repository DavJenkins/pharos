#!/usr/bin/env python3
"""Install the fixed-scope library helper. Requires explicit root execution."""
import os
import sys
from pathlib import Path
import subprocess
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from deploy.install_network_admin import install

def main():
    if os.geteuid()!=0:
        raise SystemExit('Run with root privileges after reviewing tools/library_helper.py.')
    source=Path(__file__).resolve().parents[1]/'tools/library_helper.py'
    content=source.read_bytes()
    compile(content,str(source),'exec')
    rule=b'admin ALL=(root) NOPASSWD: /usr/local/libexec/dataark-library ""\n'
    import tempfile
    with tempfile.NamedTemporaryFile() as check:
        check.write(rule)
        check.flush()
        subprocess.run(['/usr/sbin/visudo','-cf',check.name],check=True)
    install(Path('/usr/local/libexec/dataark-library'),content,0o755)
    install(Path('/etc/sudoers.d/dataark-library'),rule,0o440)
    print('Library helper installed; no downloads started.')

if __name__=='__main__':
    main()
