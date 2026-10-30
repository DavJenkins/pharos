#!/usr/bin/python3
"""Real service update/rollback acceptance. Refuses physical hardware."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from software_update import Updater,Runtime,save
from build_software_update import build

def main():
    model=Path('/sys/firmware/devicetree/base/model');dmi=Path('/sys/class/dmi/id/product_name')
    identity=' '.join(p.read_text().replace('\x00','') for p in (model,dmi) if p.exists())
    if os.geteuid()!=0 or not any(value in identity for value in ('linux,dummy-virt','QEMU','qemu')):raise SystemExit('Disposable QEMU guest and root required')
    source=Path('/opt/dataark');probe=source/'app/software_update_acceptance_probe.py'
    if probe.exists():raise SystemExit('Acceptance probe already exists; inspect the prior run')
    folder=Path('/var/lib/dataark-software-acceptance')/str(time.time_ns());folder.mkdir(parents=True,mode=0o700)
    updater=Updater();updater.state=folder/'state';updater.state.mkdir(mode=0o700);updater.trust=folder/'keys';updater.trust.mkdir(mode=0o700)
    private=folder/'fixture-private.pem';public=updater.trust/'fixture.pem'
    subprocess.run(['openssl','genpkey','-algorithm','ED25519','-out',str(private)],check=True,capture_output=True)
    subprocess.run(['openssl','pkey','-in',str(private),'-pubout','-out',str(public)],check=True,capture_output=True)
    # A bootstrapped appliance need not contain .git. This is a fixture identity.
    revision=hashlib.sha256((source/'app/main.py').read_bytes()).hexdigest()[:40]
    updater.enroll(revision,'debian13-arm64-lan')
    protected=[source/'dataark.yaml',*Path('/etc/dataark').glob('*.json'),*Path('/etc/NetworkManager/system-connections').glob('*')]
    before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected if p.is_file()}
    payload=folder/'payload';target=payload/'source/app/software_update_acceptance_probe.py';target.parent.mkdir(parents=True)
    package=folder/'fixture.tar.gz';results=[]
    def prepare(value,revision):
        target.write_text('PROBE = '+str(value)+'\n')
        build(payload,updater.receipt(),source/'requirements.txt',private,package,'acceptance-'+str(value),revision)
        return updater.stage(package)['id']
    def record(name,condition):
        if not condition:raise AssertionError(name)
        results.append(name)
    original=None
    try:
        first=prepare(1,'b'*40);original=updater.apply(first)
        record('real_service_update',original['state']=='completed' and probe.read_text()=='PROBE = 1\n')
        class RejectOnce(Runtime):
            def __init__(self):self.first=True
            def healthy(self):
                if self.first:self.first=False;return False
                return super().healthy()
        updater.runtime=RejectOnce();second=prepare(2,'c'*40)
        record('failed_health_rollback',updater.apply(second)['state']=='rolled_back' and probe.read_text()=='PROBE = 1\n')
        updater.runtime=Runtime();third=prepare(3,'d'*40)
        child=os.fork()
        if child==0:
            updater.apply(third,lambda _:os._exit(77));os._exit(1)
        _,status=os.waitpid(child,0)
        record('worker_process_interrupted',os.waitstatus_to_exitcode(status)==77 and updater.journal()['state']=='applying')
        updater.recover(boot=True)
        record('restore_before_api_restart',updater.journal()['state']=='rollback_pending_health' and probe.read_text()=='PROBE = 1\n')
        updater.runtime.start();updater.verify_recovery()
        record('post_recovery_health',updater.journal()['state']=='rolled_back' and updater.runtime.healthy())
        record('configuration_credentials_network_profiles_preserved',before=={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in before})
    finally:
        if original:
            updater.restore(original)
        private.unlink(missing_ok=True)
    record('original_software_restored',not probe.exists() and updater.runtime.healthy())
    report={'scope':'Disposable QEMU ARM64 guest; real dataark.service stop/start; no physical Ark update',
        'passed':results,'state':'passed','signing_key':'ephemeral fixture key removed','root':str(folder)}
    save(folder/'report.json',report);print(json.dumps(report,indent=2))

if __name__=='__main__':main()
