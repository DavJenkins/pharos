#!/usr/bin/python3
"""Destructive only to a newly created disposable QEMU guest; never a physical Pi.
Exercise the real stock coordinator phases; report omitted radio acceptance.
"""
from pathlib import Path
import json,os,sys,subprocess,hashlib,importlib.util,secrets,traceback,time
marker=Path('/etc/dataark-clean-bootstrap-test')
if os.geteuid()!=0 or not marker.is_file():
 raise SystemExit('Disposable clean-test guest marker and root required')
model=Path('/sys/firmware/devicetree/base/model')
product=Path('/sys/class/dmi/id/product_name')
identity=(model.read_text().replace('\x00','') if model.exists() else '')+' '+(product.read_text() if product.exists() else '')
if not any(value in identity for value in ['linux,dummy-virt','QEMU','qemu']):
 raise SystemExit('This harness refuses a physical or unrecognized machine')
kit=Path('/mnt/storage/DATA-ARK-RECOVERY');report=Path('/var/lib/dataark/clean-bootstrap-test.json');journal=Path('/var/lib/dataark/bootstrap.json')
spec=importlib.util.spec_from_file_location('bootstrap',kit/'bootstrap_stock_pi.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
c=json.loads((kit/'site.json').read_text())
if hasattr(b,'platforms'):c=b.platforms.configure(c,'debian13-arm64-lan')
else:c['baseline']['require_raspberry_pi_os']=False
# This is an explicit test-site override, not a fake Raspberry Pi OS marker.
(kit/'clean-test-site.json').write_text(json.dumps(c,indent=2))
b.validate(c);errors=b.preflight(c,kit,journal)
r={'scope':'Clean Debian 13 generic ARM64 software bootstrap; no Pi radio emulation','started_at':time.time(),'preflight_errors':errors,'source_revision':json.loads((kit/'kit.json').read_text())['source_revision'],'completed':[],'not_tested':['Pi-specific network/hotspot/portal phase','physical hardware acceptance','optional content restoration'],'status':'running'}
report.parent.mkdir(parents=True,exist_ok=True)
def save():report.write_text(json.dumps(r,indent=2))
save()
if errors:raise SystemExit('Preflight blocked: '+repr(errors))
state=json.loads(journal.read_text()) if journal.exists() else {'completed':[],'configuration_sha256':hashlib.sha256(json.dumps(c,sort_keys=True).encode()).hexdigest(),'kit_source_sha256':json.loads((kit/'kit.json').read_text())['source_sha256']}
i=b.Installer(c,kit,state,journal)
# Supply a newly generated guest-only credential to the actual installer's
# existing interactive password reader. Never print or reuse production secrets.
secret=Path('/root/clean-bootstrap-password-input');password=secrets.token_urlsafe(24)
secret.write_text(password+'\n'+password+'\n');secret.chmod(0o600)
input_stream=secret.open();os.dup2(input_stream.fileno(),0)
try:
 phases=['packages','source','storage','python']+(['platform_settings'] if hasattr(i,'platform_settings') else [])+['base_services','content_access']+(['network'] if c.get('network',{}).get('mode')=='lan' else [])+['content','finish']
 for phase in phases:
  r['active_phase']=phase;save();i.phase(phase,getattr(i,phase));r['completed'].append(phase);save()
 r['status']='software_phases_passed_radio_phase_not_run';r.pop('active_phase',None)
except BaseException as e:
 r['status']='failed';r['error']=str(e);traceback.print_exc();raise
finally:
 r['finished_at']=time.time();save();input_stream.close();secret.unlink(missing_ok=True)
