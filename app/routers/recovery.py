from fastapi import APIRouter, HTTPException
import subprocess
from tools.recovery_queue import build_presets, snapshot, ROOT
import threading,time
_preset_lock=threading.Lock()
_preset_cache={}

router = APIRouter(prefix='/recovery', tags=['Recovery'])

@router.get('/status')
def status():
    try:
        result=snapshot()
        try:
            worker=subprocess.run(['systemctl','show','-p','ActiveState','-p','Job','dataark-recovery.service'],capture_output=True,text=True,timeout=3)
            fields=dict(line.split('=',1) for line in worker.stdout.splitlines() if '=' in line)
            result['worker_active']=worker.returncode==0 and (fields.get('ActiveState') in ('active','activating','deactivating') or bool(fields.get('Job')))
        except (OSError,subprocess.TimeoutExpired):result['worker_active']=False
        if result['status']=='running' and not result['worker_active']:result['status']='interrupted'
        return result
    except (OSError, ValueError, KeyError):
        raise HTTPException(503, 'Recovery state needs caretaker attention') from None

@router.get('/presets')
def presets():
    profile = ROOT / 'config/content/content.yaml'
    try:
        with _preset_lock:
            if time.monotonic()-_preset_cache.get('time',-1000)<60:return _preset_cache['value']
            result = []
            for plan in build_presets(profile):
                result.append({'preset': plan['preset'], 'plan_id': plan['plan_id'], 'capacity': plan['capacity'],
                               'packages': len(plan['jobs']), 'first_packages': [p['title'] for p in plan['jobs'][:8]]})
            value={'presets': result, 'suggested': 'minimal' if result[1]['capacity']['fits'] else 'none',
                   'approval_required': True,'checked_at':time.time(),'hardware_acceptance': 'pending'}
            _preset_cache.update(time=time.monotonic(),value=value)
            return value
    except (OSError, ValueError, KeyError) as error:
        raise HTTPException(503, 'Cannot prepare recovery presets; check the saved profile and package estimates') from error
