from fastapi import APIRouter, HTTPException
from tools.recovery_queue import build_plan, snapshot, ROOT

router = APIRouter(prefix='/recovery', tags=['Recovery'])

@router.get('/status')
def status():
    try:
        return snapshot()
    except (OSError, ValueError, KeyError):
        raise HTTPException(503, 'Recovery state needs caretaker attention') from None

@router.get('/presets')
def presets():
    profile = ROOT / 'config/content/content.yaml'
    try:
        result = []
        for name in ('none', 'minimal', 'recommended', 'full'):
            plan = build_plan(profile, name)
            result.append({'preset': name, 'plan_id': plan['plan_id'], 'capacity': plan['capacity'],
                           'packages': len(plan['jobs']), 'first_packages': [p['title'] for p in plan['jobs'][:8]]})
        return {'presets': result, 'suggested': 'minimal' if result[1]['capacity']['fits'] else 'none',
                'approval_required': True, 'hardware_acceptance': 'pending'}
    except (OSError, ValueError, KeyError) as error:
        raise HTTPException(503, 'Cannot prepare recovery presets; check the saved profile and package estimates') from error
