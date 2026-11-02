"""Read-only previews/progress; authenticated jobs use appliance_jobs."""
import subprocess
from fastapi import APIRouter, HTTPException, Query
from tools import clone_drive

router = APIRouter(prefix='/clone', tags=['Drive cloning'])

@router.get('/drives')
def drives():
    try:
        return {'drives': clone_drive.targets()}
    except (OSError, ValueError, RuntimeError):
        raise HTTPException(503, 'Cannot inspect mounted drives') from None

@router.get('/plan')
def plan(drive: str, mode: str = Query('config', pattern='^(config|fit|populated)$')):
    try:
        target = next((item for item in clone_drive.targets() if item.get('id') == drive), None)
        if target is None:
            raise HTTPException(404, 'Mounted drive not found; reload the drive list')
        return clone_drive.summary(clone_drive.build_plan(target['path'], mode))
    except (OSError, ValueError, RuntimeError) as error:
        raise HTTPException(409, str(error)) from None

@router.get('/status')
def status():
    try:
        value=clone_drive.status()
        if value.get('state')=='queued':
            result=subprocess.run(['systemctl','show','-p','ActiveState','-p','Job','dataark-clone.service'],capture_output=True,text=True,timeout=3)
            fields=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
            if result.returncode==0 and not fields.get('Job') and fields.get('ActiveState') not in ('active','activating'):
                value.update(state='interrupted',error='The copy worker did not start. Check the destination and preview again.')
        return value
    except (OSError, ValueError, subprocess.TimeoutExpired):
        raise HTTPException(503, 'Cannot read clone progress') from None
