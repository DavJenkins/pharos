from pathlib import Path
import json,shutil
from fastapi.testclient import TestClient
from deploy.container import runtime,server

def test_no_host_mutation_path_or_docker_socket():
    client=TestClient(server.app)
    for path in ['/api/network/admin/hotspot','/api/library/remove','/api/configuration/save','/api/appliance-jobs/action','/api/bugout/start']:
        assert client.post(path,json={}).status_code==501
    assert client.get('/api/container/capabilities').json()['host_administration'] is False
    assert client.post('/api/container/reload').status_code==401

def test_cross_origin_requests_refused():
    r=TestClient(server.app).post('/api/debug/on',headers={'Origin':'https://elsewhere.invalid'})
    assert r.status_code==403

def test_browser_status_contract_excludes_invented_wifi_and_reports_health(monkeypatch):
    monkeypatch.setattr(Path,'is_mount',lambda _:True)
    monkeypatch.setattr(server,'reader_state',lambda:{'archives':0})
    value=server.status_data()
    assert value['status']['health']['state']=='ok'
    assert value['network']['capabilities']['network_controls'] is False
    assert value['network']['wifi']['state']=='not_configured' and value['network']['wifi']['enabled'] is None

def test_portable_board_and_private_state_survive_new_app_client(tmp_path,monkeypatch):
    from app.services import community
    folder=tmp_path/'community';folder.mkdir();monkeypatch.setattr(community,'DATABASE',folder/'board.sqlite3')
    client=TestClient(server.app)
    community.initialize()
    r=client.post('/api/community/threads',json={'title':'Local message','body':'**Preserved** across container recreation','category':'general','name':'Test'})
    assert r.status_code==201,r.text
    r=TestClient(server.app).get('/api/community/threads')
    assert 'Local message' in r.text

def test_empty_reader_is_a_useful_page(monkeypatch):
    monkeypatch.setattr(server,'reader_state',lambda:{'archives':0})
    r=TestClient(server.app).get('/kiwix/')
    assert r.status_code==200 and 'No offline archives installed' in r.text

def test_only_configured_safe_current_archives(tmp_path):
    (tmp_path/'current.zim').write_bytes(b'archive');(tmp_path/'old.zim').write_bytes(b'old')
    data={'assets':[{'relative_path':'current.zim'},{'relative_path':'old.zim','removed':True}]}
    assert [Path(r[0]).name for r in runtime.archives(data,tmp_path)]==['current.zim']
    import pytest
    with pytest.raises(ValueError,match='Unsafe'):runtime.archives({'assets':[{'relative_path':'../private.zim'}]},tmp_path)

def test_existing_flat_public_configuration_is_not_replaced(tmp_path):
    from app.services.configuration_project import load,dump
    source=Path(__file__).resolve().parents[1]
    config=tmp_path/'config';(config/'content').mkdir(parents=True)
    original=load(source/'config/library/ark.yaml');original['system']['project_name']='My portable Ark'
    (config/'content/public-manifest.yaml').write_text(dump(original))
    data=runtime.initialize(config,source/'config')
    assert data['system']['project_name']=='My portable Ark'
    (config/'library/ark.yaml').write_text((config/'library/ark.yaml').read_text().replace('My portable Ark','Edited Ark'))
    assert runtime.initialize(config,source/'config')['system']['project_name']=='Edited Ark'

def test_compose_is_unprivileged_and_does_not_create_missing_media():
    import yaml
    root=Path(__file__).resolve().parents[1];compose=yaml.safe_load((root/'deploy/container/compose.yaml').read_text())
    ark=compose['services']['ark'];assert ark['cap_drop']==['ALL']
    assert not any(k in ark for k in ('privileged','devices','network_mode','pid'))
    media=next(v for v in ark['volumes'] if isinstance(v,dict) and v['target']=='/mnt/storage')
    assert media['read_only'] and not media['bind']['create_host_path']
    assert 'docker.sock' not in str(compose)

def test_private_media_not_exposed_by_library_file_route():
    manifest={'assets':[{'relative_path':'archives/current.zim'}]}
    assert server.public_media_path('archives/current.zim',manifest)
    for path in ['bugout-drop/private.tar','arbitrary-private-file.txt','.dataark-private/key','forms/.secret','../etc/passwd']:
        assert not server.public_media_path(path,manifest)

def test_render_uses_image_artwork_root_and_preserves_last_working_manifest(tmp_path,monkeypatch):
    root=tmp_path/'image';config=tmp_path/'config';web=tmp_path/'web';state=tmp_path/'state'
    for p in (root,config,web,state):p.mkdir()
    (config/'manifest.yaml').write_text('previous valid manifest')
    (root/'dataark.yaml').write_text('previous valid manifest')
    (web/'index.html').write_text('<body>Last working page</body>')
    monkeypatch.setattr(runtime,'ROOT',root);monkeypatch.setattr(runtime,'CONFIG',config);monkeypatch.setattr(runtime,'WEB',web);monkeypatch.setattr(runtime,'STATE',state)
    def init(): (config/'manifest.yaml').write_text('new manifest')
    monkeypatch.setattr(runtime,'initialize',init)
    def fail(manifest,*_,**__):
        assert manifest.resolve().parent==root
        raise ValueError('Invalid edited configuration')
    monkeypatch.setattr(runtime,'build',fail);runtime.render()
    assert (root/'dataark.yaml').read_text()=='previous valid manifest'
    assert (config/'manifest.yaml').read_text()=='previous valid manifest'
    assert 'Last working page' in (web/'index.html').read_text()
    assert 'error' in json.loads((state/'rendered.json').read_text())
