#!/usr/bin/python3
"""Acceptance of real sudo boundary, systemd worker, and boot recovery on QEMU."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from software_update import Updater,Runtime,save
from build_software_update import build

def main():
    identity=' '.join(path.read_text() for path in (Path('/sys/firmware/devicetree/base/model'),Path('/sys/class/dmi/id/product_name')) if path.exists())
    if os.geteuid()!=0 or not any(value in identity for value in ('linux,dummy-virt','QEMU','qemu')) or os.uname().machine!='aarch64':raise SystemExit('Disposable ARM64 QEMU guest required')
    updater=Updater();source=Path('/opt/dataark');probe=source/'app/software_service_acceptance_probe.py'
    if probe.exists() or updater.receipt()['sequence']!=0:raise SystemExit('Expected an untouched test enrollment')
    folder=Path('/var/lib/dataark-software-service-acceptance')/str(time.time_ns());folder.mkdir(parents=True,mode=0o700)
    key=folder/'fixture-private.pem';public=updater.trust/'service-fixture.pem'
    subprocess.run(['openssl','genpkey','-algorithm','ED25519','-out',str(key)],check=True,capture_output=True)
    subprocess.run(['openssl','pkey','-in',str(key),'-pubout','-out',str(public)],check=True,capture_output=True)
    payload=folder/'payload';target=payload/'source/app/software_service_acceptance_probe.py';target.parent.mkdir(parents=True)
    package=folder/'fixture.tar.gz';results=[];original=None
    def helper(value):
        command=['runuser','-u','admin','--','sudo','-n','--','/usr/local/libexec/dataark-software-update']
        result=subprocess.run(command,input=json.dumps(value),text=True,capture_output=True,timeout=180)
        data=json.loads(result.stdout)
        if not data.get('ok'):raise ValueError(data)
        return data
    def stage(value,revision,bad=False):
        target.write_text('PROBE = '+str(value)+'\n')
        badfile=payload/'source/app/main.py'
        if bad:badfile.write_text('invalid python !!!\n')
        else:badfile.unlink(missing_ok=True)
        build(payload,updater.receipt(),source/'requirements.txt',key,package,'service-test-'+str(value),revision)
        identifier=uuid.uuid4().hex;inbox=Path('/var/lib/dataark/software-inbox')/(identifier+'.tar.gz');shutil.copyfile(package,inbox);os.chown(inbox,1000,1000)
        return helper({'action':'stage','id':identifier})['id']
    def wait():
        for _ in range(90):
            state=updater.journal()
            if state['state'] in ('completed','rolled_back','refused') and not (updater.state/'queued.json').exists():return state
            time.sleep(1)
        raise TimeoutError('Worker did not finish')
    def record(name,condition):
        if not condition:raise AssertionError(name)
        results.append(name)
    try:
        record('root_helper_status_as_admin',helper({'action':'status'})['configured'])
        identifier=stage(1,'b'*40);helper({'action':'apply','id':identifier});original=wait()
        record('systemd_worker_applied_signed_package',original['state']=='completed' and probe.read_text()=='PROBE = 1\n')
        identifier=stage(2,'c'*40,bad=True);helper({'action':'apply','id':identifier});rolled=wait()
        record('invalid_api_release_automatically_rolled_back',rolled['state']=='rolled_back' and Runtime().healthy())
        identifier=stage(3,'d'*40);child=os.fork()
        if child==0:
            updater.apply(identifier,lambda _:os._exit(77));os._exit(1)
        _,code=os.waitpid(child,0);record('interrupted_actual_installation',os.waitstatus_to_exitcode(code)==77)
        subprocess.run(['systemctl','restart','dataark-software-boot-recover.service'],check=True)
        record('boot_unit_restored_before_api',updater.journal()['state']=='rollback_pending_health' and probe.read_text()=='PROBE = 1\n')
        subprocess.run(['systemctl','start','dataark.service'],check=True)
        subprocess.run(['systemctl','restart','dataark-software-verify-recovery.service'],check=True)
        record('post_boot_recovery_verified',updater.journal()['state']=='rolled_back' and Runtime().healthy())
    finally:
        if original:updater.restore(original)
        key.unlink(missing_ok=True);public.unlink(missing_ok=True)
        subprocess.run(['systemctl','reset-failed','dataark.service'],check=False,capture_output=True)
    record('original_emulator_restored',not probe.exists() and Runtime().healthy() and updater.receipt()['sequence']==0)
    report={'state':'passed','passed':results,'scope':'ARM64 QEMU: actual sudoers/helper, systemd install, broken API rollback, boot restore/verify units','fixture_private_key_removed':True}
    save(folder/'report.json',report);print(json.dumps(report,indent=2))

if __name__=='__main__':main()
