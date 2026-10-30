"""Capacity-aware public restore plans and a durable, explicitly approved queue.
No formatting or removal operations. CLI mutations require local root access.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import content_profile as content

STATE = Path('/var/lib/dataark/recovery')
POLICY = ROOT / 'config/recovery-presets.json'
GROUPS = ('archives', 'direct_files', 'map_files', 'recipes')
FINISHED = {'complete', 'failed', 'blocked', 'cancelled'}


def save(path, value):
    """Persist before reporting success; replace atomically and fsync the directory."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.part')
    with temporary.open('w') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(temporary, 0o644)
    temporary.replace(path)
    descriptor = os.open(path.parent, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def fingerprint(profile, policy):
    c = content.read(profile)
    h = hashlib.sha256(json.dumps(policy, sort_keys=True).encode())
    for source in ['app/services/collection_variants.py','tools/recovery_queue.py','tools/content_profile.py','tools/content_lock.py','tools/content_types.py','app/services/configuration_project.py','tools/configuration_project.py'] + [v[0] for v in content.COLLECTIONS.values()]:
        h.update(source.encode() + b'\0' + (ROOT/source).read_bytes() + b'\0')
    for path, name in sorted(content.portable_files(c, Path(profile).parent), key=lambda pair: pair[1]):
        h.update(name.encode() + b'\0' + path.read_bytes() + b'\0')
    return h.hexdigest()


def packages(c, policy):
    """Profiles carry measured recipe bounds; unknown bounds remain unknown."""
    from app.services.collection_variants import recovery_archives
    excluded=recovery_archives(c,policy)
    result = []
    for group in GROUPS:
        for original in c.get(group, []):
            if not original.get('enabled', True) or (group=='archives' and original['id'] in excluded):
                continue
            item = copy.deepcopy(original)
            size = item.get('installed_bytes', item.get('bytes'))
            if type(size) is not int or size < 0:
                size = None
            if group == 'recipes':
                tier = policy['recipe_tiers'].get(item['id'], 'full')
            elif group == 'archives':
                tier = 'recommended' if item['id'] in policy['recommended_archives'] else 'full'
            elif group == 'map_files':
                tier = 'full'
            elif item.get('path', '').startswith('preparedness/'):
                tier = 'minimal' if size is not None and size <= policy['minimal_file_max_bytes'] else 'recommended'
            elif item.get('path', '').startswith('vehicles/'):
                tier = 'recommended'
            else:
                tier = 'full'
            temp = item.get('temporary_bytes', size)
            headroom = item.get('update_headroom_bytes', max(16 * 1024**2, size // 5) if size is not None else None)
            for value in (temp, headroom):
                if value is not None and (type(value) is not int or value < 0):
                    raise ValueError('Invalid package capacity estimate: ' + item['id'])
            result.append({'id': item['id'], 'kind': 'recipe' if group == 'recipes' else group,
                           'title': item.get('title', item['id']), 'tier': tier, 'item': item,
                           'installed_bytes': size, 'temporary_bytes': temp,
                           'update_headroom_bytes': headroom, 'requires': list(item.get('requires', []))})
    ids = [p['id'] for p in result]
    if len(ids) != len(set(ids)):
        raise ValueError('Recovery package identifiers must be unique across all groups')
    return result


def order(chosen):
    remaining = {p['id']: p for p in chosen}
    done, output = set(), []
    while remaining:
        ready = [p for p in remaining.values() if set(p['requires']) <= done]
        if not ready:
            raise ValueError('Missing or cyclic package dependency')
        ready.sort(key=lambda p: (p['id'] == 'indexes', p['installed_bytes'] is None,
                                  p['installed_bytes'] or 0, p['id']))
        p = ready[0]
        output.append(p)
        done.add(p['id'])
        del remaining[p['id']]
    return output


def build_plan(profile, preset, policy=None, free_bytes=None):
    profile = Path(profile).resolve()
    policy = policy or json.loads(POLICY.read_text())
    if preset not in ('none', 'minimal', 'recommended', 'full'):
        raise ValueError('Unknown recovery preset')
    c = content.read(profile)
    content.validate(c)
    all_packages = {p['id']: p for p in packages(c, policy)}
    tiers = {'none': set(), 'minimal': {'minimal'}, 'recommended': {'minimal', 'recommended'},
             'full': {'minimal', 'recommended', 'full'}}[preset]
    chosen = {p['id'] for p in all_packages.values() if p['tier'] in tiers and p['id'] != 'indexes'}
    def include(identifier, trail=()):
        if identifier in trail:
            raise ValueError('Cyclic recovery dependency')
        if identifier not in all_packages:
            raise ValueError('Required package is disabled or missing: ' + identifier)
        chosen.add(identifier)
        for dependency in all_packages[identifier]['requires']:
            include(dependency, trail + (identifier,))
    for identifier in list(chosen):
        include(identifier)
    if chosen and 'indexes' in all_packages:
        chosen.add('indexes')
        all_packages['indexes']['requires'] = sorted(chosen - {'indexes'})
    jobs = order([all_packages[key] for key in chosen])
    root = Path(c['content_root']).resolve()
    free = shutil.disk_usage(root).free if free_bytes is None else free_bytes
    unknown, additional, headroom, peak = [], 0, 0, 0
    for job in jobs:
        present = False
        item = job['item']
        if job['kind'] != 'recipe':
            target = content.inside(root, item['path'])
            present = target.is_file() and item.get('bytes') is not None and target.stat().st_size == item['bytes']
        # Size matching only affects capacity. Execution still verifies recorded hashes.
        job['present_for_capacity'] = present
        if any(job[key] is None for key in ('installed_bytes', 'temporary_bytes', 'update_headroom_bytes')):
            unknown.append(job['id'])
            continue
        # Recipes deliberately budget their full bounded footprint, even when partially present.
        extra = 0 if present else job['installed_bytes']
        peak = max(peak, additional + job['temporary_bytes'] + extra)
        additional += extra
        headroom += job['update_headroom_bytes']
    reserve = int(max(c['reserve_gib'], policy['reserve_gib']) * 1024**3)
    required = max(additional, peak) + headroom + reserve if jobs else 0
    body = {'schema': 1, 'preset': preset, 'profile': str(profile), 'content_root': str(root),
            'profile_sha256': fingerprint(profile, policy), 'policy': policy, 'jobs': jobs,
            'capacity': {'free_bytes': free, 'additional_bytes': additional, 'temporary_peak_bytes': peak,
                         'update_headroom_bytes': headroom, 'reserve_bytes': reserve,
                         'required_free_bytes': required, 'unknown_packages': unknown,
                         'fits': not unknown and free >= required},
            'note': 'Conservative package estimates, not a future publisher-size guarantee. No content is removed.'}
    identity = copy.deepcopy(body)
    identity['capacity'].pop('free_bytes')
    identity['capacity'].pop('fits')
    body['plan_id'] = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return body


def create(plan, accepted, directory=STATE):
    if accepted != plan['plan_id']:
        raise ValueError('Accept the exact reviewed plan_id; regenerate the plan after changes')
    if not plan['capacity']['fits']:
        raise ValueError('Preset does not fit, or package sizes are unknown')
    directory = Path(directory)
    if (directory / 'queue.json').exists():
        raise ValueError('A queue already exists; use resume/restart/cancel or archive it explicitly')
    queue = copy.deepcopy(plan)
    queue.update(status='approved', approved_at=time.time(), updated_at=time.time(), events=[])
    for job in queue['jobs']:
        job.update(status='queued', attempts=0, error=None)
    save(directory / 'queue.json', queue)
    return queue


def control(action, directory=STATE):
    if action not in ('pause', 'cancel'):
        raise ValueError('Unknown queue control')
    if not (Path(directory) / 'queue.json').exists():
        raise ValueError('No recovery queue exists')
    save(Path(directory) / 'control.json', {'action': action, 'requested_at': time.time()})


def snapshot(directory=STATE):
    path = Path(directory) / 'queue.json'
    if not path.exists():
        return {'status': 'not_started', 'jobs': [], 'completed': 0, 'total': 0}
    q = json.loads(path.read_text())
    jobs = []
    try:current_progress=json.loads((Path(directory)/'progress.json').read_text())
    except (OSError,ValueError):current_progress={}
    for p in q['jobs']:
        partial = 0
        if p['kind'] != 'recipe':
            target = content.inside(Path(q['content_root']), p['item']['path'])
            part = Path(q['content_root']) / '.dataark-restoration' / (hashlib.sha256(p['item']['path'].encode()).hexdigest() + '.part')
            try:
                if part.is_file():partial = part.stat().st_size
            except PermissionError:
                partial = p.get('partial_bytes', 0)
        if current_progress.get('package')==p['id'] and p['status']=='running':
            partial=current_progress.get('partial_bytes',partial)
            p={**p,'phase':current_progress.get('phase',p.get('phase'))}
        jobs.append({key: p.get(key) for key in ('id', 'title', 'status', 'phase', 'attempts', 'error', 'installed_bytes')} | {'partial_bytes': partial, 'path': p['item'].get('path') if p['status'] == 'complete' else None})
    return {'status': q['status'], 'preset': q['preset'], 'updated_at': q['updated_at'],
            'completed': sum(j['status'] == 'complete' for j in jobs), 'total': len(jobs),
            'capacity': q['capacity'], 'message': q.get('message'), 'jobs': jobs}


def transition(q, directory, status, job=None, error=None):
    q['status'] = status if job is None else 'running'
    q['updated_at'] = time.time()
    if job is not None:
        job['status'] = status if status in ('running', 'complete', 'failed', 'blocked') else job['status']
        job['error'] = error
    q['events'] = (q.get('events', []) + [{'at': q['updated_at'], 'state': status, 'package': job['id'] if job else None}])[-200:]
    save(Path(directory) / 'queue.json', q)


def execute_job(q, job, directory=STATE):
    c = content.read(q['profile'])
    root = Path(q['content_root'])
    def phase(name):
        save(Path(directory) / 'phase.json', {'package':job['id'],'phase':name,'updated_at':time.time()})
    if job['kind'] == 'recipe':
        phase('restoring_collection')
        content.recipe(job['item'], c, root, Path(q['profile']).parent, progress=phase)
    else:
        # A matching size alone is not enough to reuse a pinned original.
        from tools.content_types import Context, dispatch
        dispatch(job['kind'], 'restore', job['item'], Context(root, c, Path(q['profile']).parent, progress=phase))
        if job['kind'] == 'archives':
            phase('publishing_reader')
            from tools.publish_content import publish
            publish(root)
            subprocess.run(['docker','restart','kiwix-serve'],check=True)
            subprocess.run(['bash',str(ROOT/'deploy/deploy-web.sh')],check=True)



def stop_child(process):
    if process.poll() is not None:return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()


def child(q, job, directory):
    log = Path(directory) / 'worker.log'
    descriptor = int(os.environ['DATAARK_CONTENT_LOCK_FD'])
    with log.open('ab') as output:
        with subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '_execute', '--state', str(directory), '--job', job['id']],
                              stdout=output, stderr=output, start_new_session=True, pass_fds=(descriptor,)) as process:
            try:
                while process.poll() is None:
                    if shutil.disk_usage(q['content_root']).free < q['capacity']['reserve_bytes']:
                        save(Path(directory) / 'control.json', {'action':'pause','requested_at':time.time()})
                    if (Path(directory) / 'control.json').exists():
                        stop_child(process)
                        return 'interrupted'
                    phase_path=Path(directory) / 'phase.json'
                    if phase_path.exists():
                        current=json.loads(phase_path.read_text())
                        if current['package']==job['id'] and current['phase']!=job.get('phase'):
                            job['phase']=current['phase']
                            save(Path(directory)/'progress.json',{'package':job['id'],'phase':job['phase'],'partial_bytes':job.get('partial_bytes',0),'updated_at':time.time()})
                    if job['kind'] != 'recipe':
                        part = content.staging_path(Path(q['content_root']), job['item']['path'])
                        amount = part.stat().st_size if part.is_file() else 0
                        if amount != job.get('partial_bytes', 0):
                            job['partial_bytes'] = amount
                            save(Path(directory)/'progress.json',{'package':job['id'],'phase':job.get('phase'),'partial_bytes':amount,'updated_at':time.time()})
                    time.sleep(1)
                return process.returncode
            finally:
                stop_child(process)


def run(directory=STATE, restart=False, runner=child):
    directory = Path(directory)
    q = json.loads((directory / 'queue.json').read_text())
    if fingerprint(q['profile'], q['policy']) != q['profile_sha256']:
        raise ValueError('Profile/catalogues changed; preserve this queue and approve a new plan')
    if q['status'] == 'complete' and all(j['status']=='complete' for j in q['jobs']) and not restart:
        return q
    # Approval survives interruption, but never silently follows a changed profile.
    (directory / 'control.json').unlink(missing_ok=True)
    for job in q['jobs']:
        if restart or job['status'] != 'complete':
            job.update(status='queued', error=None)
    transition(q, directory, 'running')
    for job in q['jobs']:
        if job['status'] == 'complete':
            continue
        control_path = directory / 'control.json'
        if control_path.exists():
            action = json.loads(control_path.read_text())['action']
            transition(q, directory, 'paused' if action == 'pause' else 'cancelled')
            return q
        dependencies = [p for p in q['jobs'] if p['id'] in job['requires']]
        if any(p['status'] != 'complete' for p in dependencies):
            transition(q, directory, 'blocked', job, 'A dependency needs attention')
            continue
        reserve = q['capacity']['reserve_bytes']
        present=False
        if job['kind']!='recipe':
            target=content.inside(Path(q['content_root']),job['item']['path'])
            present=target.is_file() and job['item'].get('bytes') is not None and target.stat().st_size==job['item']['bytes']
        need = (0 if present else (job['installed_bytes'] or 0)) + (job['temporary_bytes'] or 0) + reserve
        if shutil.disk_usage(q['content_root']).free < need:
            transition(q, directory, 'paused', error='Available space changed')
            q['message'] = 'Available space changed; free space or approve a smaller preset'
            save(directory / 'queue.json', q)
            return q
        job['attempts'] += 1
        transition(q, directory, 'running', job)
        try:
            result = runner(q, job, directory)
            if result == 'interrupted':
                job['status'] = 'queued'
                action = json.loads(control_path.read_text())['action']
                transition(q, directory, 'paused' if action == 'pause' else 'cancelled')
                return q
            if result:
                raise RuntimeError('Package failed; inspect the caretaker worker log')
            transition(q, directory, 'complete', job)
        except Exception as error:
            transition(q, directory, 'failed', job, str(error))
    transition(q, directory, 'needs_attention' if any(p['status'] != 'complete' for p in q['jobs']) else 'complete')
    return q


def lock(path):
    import fcntl
    path.parent.mkdir(parents=True, exist_ok=True)
    stream = path.open('a')
    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
    return stream


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['plan', 'create', 'run', 'resume', 'restart', 'pause', 'cancel', 'status', '_execute'])
    p.add_argument('--profile', type=Path, default=ROOT / 'config/content/content.yaml')
    p.add_argument('--preset', choices=['none', 'minimal', 'recommended', 'full'], default='minimal')
    p.add_argument('--state', type=Path, default=STATE)
    p.add_argument('--accept-plan')
    p.add_argument('--job')
    a = p.parse_args()
    if a.action == 'plan':
        print(json.dumps(build_plan(a.profile, a.preset), indent=2))
        return
    if a.action == 'status':
        print(json.dumps(snapshot(a.state), indent=2))
        return
    if os.geteuid() != 0:
        raise SystemExit('Queue changes require local caretaker access through sudo')
    if a.action in ('pause', 'cancel'):
        control(a.action, a.state)
        return
    if a.action == '_execute':
        q = json.loads((a.state / 'queue.json').read_text())
        execute_job(q, next(j for j in q['jobs'] if j['id'] == a.job), a.state)
        return
    queue_lock = lock(a.state / 'queue.lock')
    if a.action == 'create':
        create(build_plan(a.profile, a.preset), a.accept_plan, a.state)
        return
    q = json.loads((a.state / 'queue.json').read_text())
    if Path(q['content_root']) != Path('/mnt/storage') or not Path(q['content_root']).is_mount():
        raise SystemExit('Recovery requires the mounted content SSD at /mnt/storage')
    worker_lock = lock(Path('/var/lib/dataark/updates/worker.lock'))
    map_lock = lock(Path('/var/lib/dataark/maps/worker.lock'))
    os.environ['DATAARK_CONTENT_LOCK_FD'] = str(worker_lock.fileno())
    if fingerprint(q['profile'], q['policy']) != q['profile_sha256']:
        raise SystemExit('Profile changed; approve a new plan before applying selections')
    if q['jobs']:
        content.apply_public_profile(content.read(q['profile']), Path(q['profile']).parent,q['policy'].get('variant_preferences',{}))
    run(a.state, restart=a.action == 'restart')


if __name__ == '__main__':
    main()
