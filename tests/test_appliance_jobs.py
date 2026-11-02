import json
from types import SimpleNamespace
import pytest
from tools import appliance_jobs as a,clone_drive as clone,recovery_queue as queue

@pytest.mark.parametrize('data',[{},[],{'action':'shell','command':'id'},
 {'action':'clone_start','plan_id':'x'}, {'action':'discover','path':'/etc'},
 {'action':'clone_preview','uuid':'../../dev/sda','mode':'fit'},
 {'action':'clone_preview','uuid':'abcd-1234','mode':'erase'},
 {'action':'restore_start','preset':'full','plan_id':'a'*64,'replace_finished':'true'},
 {'action':'restore_resume','profile':'/tmp/untrusted.yaml'}])
def test_request_boundary_rejects_commands_paths_and_bad_fields(data):
    with pytest.raises(ValueError):a.validate(data)

def fixture(monkeypatch,tmp_path):
    monkeypatch.setattr(a,'PRIVATE',tmp_path)
    monkeypatch.setattr(a,'active',lambda _:False)
    monkeypatch.setattr(a,'emit',lambda *_:None)
    started=[];monkeypatch.setattr(a,'start',started.append)
    monkeypatch.setattr(queue,'STATE',tmp_path/'queue')
    return started

def test_changed_clone_plan_never_starts(monkeypatch,tmp_path):
    started=fixture(monkeypatch,tmp_path)
    plan={'plan_id':'a'*64,'mode':'fit','target':{'path':'/safe/destination'}}
    (tmp_path/'clone-plan.json').write_text(json.dumps(plan))
    monkeypatch.setattr(clone,'build_plan',lambda *_:{'plan_id':'b'*64,'fits':True})
    with pytest.raises(ValueError,match='changed'):a.dispatch({'action':'clone_start','plan_id':'a'*64})
    assert started==[]

def test_clone_capacity_failure_never_starts(monkeypatch,tmp_path):
    started=fixture(monkeypatch,tmp_path)
    plan={'plan_id':'a'*64,'mode':'populated','target':{'path':'/safe/destination'}}
    (tmp_path/'clone-plan.json').write_text(json.dumps(plan));monkeypatch.setattr(clone,'build_plan',lambda *_:{'plan_id':'a'*64,'fits':False})
    with pytest.raises(ValueError,match='does not fit'):a.dispatch({'action':'clone_start','plan_id':'a'*64})
    assert started==[]

def test_unknown_restore_sizes_never_create_or_start(monkeypatch,tmp_path):
    started=fixture(monkeypatch,tmp_path);created=[]
    monkeypatch.setattr(queue,'build_plan',lambda *_:{'plan_id':'a'*64,'capacity':{'fits':False}})
    monkeypatch.setattr(queue,'create',lambda *_:created.append(True))
    with pytest.raises(ValueError,match='sizes are unknown'):a.dispatch({'action':'restore_start','preset':'full','plan_id':'a'*64,'replace_finished':False})
    assert not created and not started

def test_finished_queue_history_is_preserved(tmp_path):
    state=tmp_path/'recovery';state.mkdir();(state/'queue.json').write_text('{"status":"complete"}');(state/'worker.log').write_text('evidence');(state/'queue.lock').touch()
    a.archive_finished(SimpleNamespace(STATE=state))
    history=list((tmp_path/'recovery-history').iterdir());assert len(history)==1
    assert json.loads((history[0]/'queue.json').read_text())['status']=='complete'
    assert (history[0]/'worker.log').read_text()=='evidence'
    assert (state/'queue.lock').exists() and not (state/'queue.json').exists()

def test_unfinished_queue_cannot_be_archived(tmp_path):
    (tmp_path/'queue.json').write_text('{"status":"paused"}')
    with pytest.raises(ValueError,match='Finish or cancel'):a.archive_finished(SimpleNamespace(STATE=tmp_path))
    assert (tmp_path/'queue.json').exists()

def test_cancel_without_queue_does_not_create_one(monkeypatch,tmp_path):
    fixture(monkeypatch,tmp_path)
    with pytest.raises(ValueError,match='No restoration queue'):a.dispatch({'action':'restore_cancel'})
    assert not (queue.STATE/'queue.json').exists()

def test_resume_changed_profile_refused(monkeypatch,tmp_path):
    started=fixture(monkeypatch,tmp_path);queue.STATE.mkdir();(queue.STATE/'queue.json').write_text(json.dumps({'profile':'profile','policy':{},'profile_sha256':'old','status':'paused'}))
    monkeypatch.setattr(queue,'fingerprint',lambda *_:'new')
    with pytest.raises(ValueError,match='configuration changed'):a.dispatch({'action':'restore_resume'})
    assert not started

def test_eject_never_unmounts_unreviewed_drive(monkeypatch,tmp_path):
    fixture(monkeypatch,tmp_path);monkeypatch.setattr(clone,'status',lambda:{'state':'copying','target_uuid':'abcd-1234'})
    with pytest.raises(ValueError,match='Only the completed copy'):a.dispatch({'action':'clone_eject','uuid':'abcd-1234'})

def test_running_copy_cannot_be_replaced(monkeypatch,tmp_path):
    fixture(monkeypatch,tmp_path);monkeypatch.setattr(a,'active',lambda _:True)
    with pytest.raises(ValueError,match='already running'):a.dispatch({'action':'clone_preview','uuid':'abcd-1234','mode':'fit'})

def test_ambiguous_drive_uuid_is_never_mounted(monkeypatch,tmp_path):
    fixture(monkeypatch,tmp_path)
    monkeypatch.setattr(a,'storage_module',lambda:SimpleNamespace(devices=lambda:[{'uuid':'abcd-1234'},{'uuid':'abcd-1234'}],mounted=lambda _:pytest.fail('Must not mount ambiguous device')))
    with pytest.raises(ValueError,match='ambiguous'):a.dispatch({'action':'clone_preview','uuid':'abcd-1234','mode':'config'})

def test_approved_clone_job_is_a_separate_snapshot(monkeypatch,tmp_path):
    started=fixture(monkeypatch,tmp_path)
    plan={'plan_id':'a'*64,'mode':'config','target':{'path':'/safe/destination'},'fits':True,'selected':[]}
    (tmp_path/'clone-plan.json').write_text(json.dumps(plan))
    monkeypatch.setattr(clone,'build_plan',lambda *_:dict(plan))
    monkeypatch.setattr(a,'save',lambda p,v:p.write_text(json.dumps(v)))
    monkeypatch.setattr(clone,'save',lambda *_:None)
    result=a.dispatch({'action':'clone_start','plan_id':'a'*64})
    (tmp_path/'clone-plan.json').write_text('{"plan_id":"unapproved later preview"}')
    assert json.loads((tmp_path/'clone-job.json').read_text())['plan_id']=='a'*64
    assert started==['dataark-clone.service'] and result['queued']

def test_api_rejects_unauthenticated_action_before_helper(monkeypatch):
    import asyncio
    from fastapi import HTTPException
    from starlette.requests import Request
    from app.routers import appliance_jobs as api
    monkeypatch.setattr(api,'authorized',lambda _:False)
    monkeypatch.setattr(api,'invoke',lambda _:pytest.fail('Unauthenticated request reached helper'))
    request=Request({'type':'http','method':'POST','path':'/','headers':[(b'host',b'dataark')]})
    with pytest.raises(HTTPException) as error:asyncio.run(api.action(request))
    assert error.value.status_code==401

def test_api_rejects_foreign_origin_before_authentication(monkeypatch):
    import asyncio
    from fastapi import HTTPException
    from starlette.requests import Request
    from app.routers import appliance_jobs as api
    monkeypatch.setattr(api,'authorized',lambda _:pytest.fail('Foreign origin reached authentication'))
    request=Request({'type':'http','method':'POST','path':'/','headers':[(b'host',b'dataark'),(b'origin',b'http://foreign.example')]})
    with pytest.raises(HTTPException) as error:asyncio.run(api.action(request))
    assert error.value.status_code==403

def test_batched_previews_match_fresh_mutation_plans(monkeypatch,tmp_path):
    import copy
    policy={'reserve_gib':10,'minimal_file_max_bytes':16*1024**2,'recommended_archives':[],'recipe_tiers':{}}
    path=tmp_path/'policy.json';path.write_text(json.dumps(policy));monkeypatch.setattr(queue,'POLICY',path)
    c={'content_root':str(tmp_path),'reserve_gib':10,'archives':[],'recipes':[],'map_files':[],
       'direct_files':[{'id':'guide','path':'preparedness/guide.pdf','bytes':10}]}
    monkeypatch.setattr(queue.content,'read',lambda _:copy.deepcopy(c))
    monkeypatch.setattr(queue.content,'validate',lambda _:None)
    monkeypatch.setattr(queue,'fingerprint',lambda *_:'same-reviewed-profile')
    monkeypatch.setattr(queue.shutil,'disk_usage',lambda _:SimpleNamespace(free=100*1024**3))
    batch=queue.build_presets(tmp_path/'content.yaml')
    fresh=[queue.build_plan(tmp_path/'content.yaml',name) for name in ('none','minimal','recommended','full')]
    assert batch==fresh
