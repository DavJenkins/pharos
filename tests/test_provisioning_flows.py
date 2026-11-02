import base64,hashlib,json,os,re,tarfile,io
from pathlib import Path
from types import SimpleNamespace
import pytest
from tools import prepare_recipient as recipient,ready_card,ready_card_writer as writer,storage_workflows as storage
from deploy import bootstrap_stock_pi as bootstrap

def managed(root,profile='debian13-amd64-lan'):
    for name in ['etc/dataark','etc/systemd/system','etc/ssh','home/admin','root','var/lib/dataark','opt/dataark/config','boot/firmware','etc/NetworkManager/system-connections']:(root/name).mkdir(parents=True,exist_ok=True)
    (root/'etc/systemd/system/dataark.service').write_text('[Service]\n')
    (root/'etc/dataark/network-admin.json').write_text('{"hash":"old"}')
    (root/'etc/hosts').write_text('127.0.0.1 localhost\n127.0.1.1 old-host\n')
    (root/'etc/machine-id').write_text('original')
    (root/'opt/dataark/config/installed-site.json').write_text(json.dumps({'platform_profile':profile}))

def test_single_launcher_accepts_only_an_unblocked_review():
    assert bootstrap.wizard_apply({'plan_id':'a'},[],lambda _:'yes')
    assert not bootstrap.wizard_apply({'plan_id':'a'},[],lambda _:'no')
    assert not bootstrap.wizard_apply({},['missing hardware'],lambda _:pytest.fail('Blocked plan asked for approval'))

@pytest.mark.parametrize('profile',['debian13-amd64-lan','debian13-arm64-lan','raspberry-pi-debian13-arm64'])
def test_recipient_preparation_is_not_limited_to_demo_media(tmp_path,profile):
    managed(tmp_path,profile);assert recipient.inspection(tmp_path)['eligible']
    recipient.arm(tmp_path,code='0007',hostname='dataark-aabbccddeeff')
    assert (tmp_path/'etc/machine-id').read_text()=='original'
    sheet=recipient.welcome_sheet(tmp_path)
    assert '0007' in sheet and 'dataark-aabbccddeeff' in sheet
    assert ('Ethernet' in sheet)==profile.endswith('-lan')
    recipient.first_boot(tmp_path)
    assert json.loads((tmp_path/'var/lib/dataark/recipient.json').read_text())['state']=='awaiting_local_password'

def test_owner_credentials_block_without_exposing_their_values(tmp_path):
    managed(tmp_path);secret='do-not-expose-this-token'
    (tmp_path/'etc/dataark/custom-client.json').write_text(json.dumps({'nested':{'api_key':secret}}))
    result=recipient.inspection(tmp_path)
    assert not result['eligible'] and secret not in json.dumps(result)
    with pytest.raises(ValueError,match='credentials'):recipient.arm(tmp_path)
    assert (tmp_path/'etc/machine-id').read_text()=='original'

def test_private_network_added_after_review_stops_first_boot(tmp_path):
    managed(tmp_path);recipient.arm(tmp_path)
    (tmp_path/'etc/NetworkManager/system-connections/private.nmconnection').write_text('[connection]\ntype=wireguard\n[wireguard]\nprivate-key=secret\n')
    with pytest.raises(ValueError,match='network authentication'):recipient.first_boot(tmp_path)
    assert (tmp_path/'etc/machine-id').read_text()=='original'

def test_upstream_wifi_removed_but_hotspot_preserved(tmp_path):
    managed(tmp_path,'raspberry-pi-debian13-arm64');folder=tmp_path/'etc/NetworkManager/system-connections'
    (folder/'hotspot').write_text('[connection]\ntype=wifi\nuuid=old\n[ipv4]\nmethod=shared\n[wifi]\nssid=My Ark\n')
    (folder/'upstream').write_text('[connection]\ntype=wifi\n[ipv4]\nmethod=auto\n[wifi-security]\npsk=private\n')
    recipient.arm(tmp_path);assert 'My Ark' in recipient.welcome_sheet(tmp_path)
    recipient.first_boot(tmp_path)
    assert (folder/'hotspot').exists() and not (folder/'upstream').exists()
    assert 'uuid = old' not in (folder/'hotspot').read_text()

def test_card_seed_has_fresh_identity_and_no_common_password_or_ssh_key():
    c={'library_gib':4,'country':'US','kit_sha256':'a'*64}
    one,cloud,sheet=writer.make_seed(c,b'print("builder")');two,_,_=writer.make_seed(c,b'print("builder")')
    assert one['hostname']!=two['hostname'] and re.fullmatch('[0-9]{4}',one['pairing_code'])
    assert cloud['users'][0]['lock_passwd'] and 'ssh_authorized_keys' not in cloud['users'][0]
    assert 'password' not in cloud['users'][0]
    assert cloud['runcmd'][-1]==['systemctl','enable','--now','dataark-card-build.service']
    assert base64.b64decode(cloud['write_files'][0]['content'])==b'print("builder")'
    assert one['pairing_code'] in sheet and 'private' in sheet.lower()

def test_card_image_hash_checked_before_any_write(tmp_path):
    p=tmp_path/'image.xz';p.write_bytes(b'not an OS')
    c={'image':{'download_bytes':p.stat().st_size,'download_sha256':'0'*64}}
    with pytest.raises(ValueError,match='No media written'):writer.validate_image(p,c)
    assert p.read_bytes()==b'not an OS'

@pytest.mark.parametrize('gib,country',[(True,'US'),(1,'US'),(1025,'US'),(4,'usa'),(4,'../')])
def test_card_parameters_are_bounded(gib,country):
    with pytest.raises(ValueError):ready_card.validate(gib,country)

def test_drive_receipt_paths_cannot_escape(tmp_path):
    (tmp_path/'CLONE-REPORT.json').write_text(json.dumps({'files':[{'path':'../../etc/shadow','sha256':'a'*64}]}))
    with pytest.raises(ValueError,match='Unsafe relative'):storage.receipts(tmp_path)

def test_conflicting_drive_receipts_refused(tmp_path):
    (tmp_path/'CLONE-REPORT.json').write_text(json.dumps({'files':[{'path':'book','sha256':'a'*64},{'path':'book','sha256':'b'*64}]}))
    with pytest.raises(ValueError,match='Conflicting'):storage.receipts(tmp_path)

def test_adoption_never_combines_copy_with_existing_payload():
    with pytest.raises(ValueError,match='never overwrites'):storage.plan('abcd-1234','adopt','drive',True)

def test_replacement_cannot_discard_saved_configuration():
    with pytest.raises(ValueError,match='keeps the saved'):storage.plan('abcd-1234','replace','drive',False)

def test_public_drive_profile_passes_installed_validators(tmp_path):
    from tools.content_profile import mirror,read
    p=Path(__file__).resolve().parents[1]/'config/content/content.yaml'
    mirror(read(p),p.parent,tmp_path/'DATA-ARK-CONFIG')
    recipe,manifest,hashes=storage.public_profile(tmp_path)
    assert recipe['schema']==1 and manifest['assets'] and hashes
    (tmp_path/'DATA-ARK-CONFIG/config/content/extra.py').write_text('raise RuntimeError()')
    with pytest.raises(ValueError,match='executable or unsupported'):storage.public_profile(tmp_path)

def test_drive_configuration_replacement_has_repeatable_rollback(tmp_path,monkeypatch):
    from tools.content_profile import mirror,read
    import shutil
    source=Path(__file__).resolve().parents[1];drive=tmp_path/'drive';root=tmp_path/'host';backup=tmp_path/'backup'
    p=source/'config/content/content.yaml';mirror(read(p),p.parent,drive/'DATA-ARK-CONFIG')
    _,public,hashes=storage.public_profile(drive)
    (root/'config').mkdir(parents=True);backup.mkdir()
    # Host-only system settings must survive using a drive's public collection.
    from app.services.configuration_project import dump
    host={**public,'system':{**public['system'],'base_mount':'/host-owned-layout'}}
    (root/'dataark.yaml').write_text(dump(host))
    (root/'config/library').mkdir();(root/'config/library/sentinel').write_text('previous authoring tree')
    shutil.copytree(root/'config/library',backup/'config-library');shutil.copy(root/'dataark.yaml',backup/'dataark.yaml')
    fstab=tmp_path/'fstab';fstab.write_text('original mount\n');shutil.copy(fstab,backup/'fstab')
    monkeypatch.setattr(storage,'ROOT',root)
    storage.adopt_configuration(drive,{'configuration':'drive','profile_hashes':hashes},backup,None)
    assert read(root/'dataark.yaml')['system']['base_mount']=='/host-owned-layout'
    x=SimpleNamespace(FSTAB=fstab)
    storage.restore_backup({'backup':str(backup),'config_trees':['library']},x)
    storage.restore_backup({'backup':str(backup),'config_trees':['library']},x)
    assert (root/'config/library/sentinel').read_text()=='previous authoring tree'
    assert not (root/'config/content').exists()
    assert (root/'dataark.yaml').read_text()==(backup/'dataark.yaml').read_text()

@pytest.mark.skipif(os.name!='posix',reason='Real PTY and Linux mount behavior')
def test_card_builder_rejects_archive_traversal(tmp_path):
    from tools.ready_card_first_boot import extract
    path=tmp_path/'bad.tar.gz'
    with tarfile.open(path,'w:gz') as z:
        entry=tarfile.TarInfo('../escape');entry.size=4;z.addfile(entry,io.BytesIO(b'nope'))
    with pytest.raises(ValueError,match='Unsafe kit'):extract(path,tmp_path/'target')
    assert not (tmp_path/'escape').exists()

@pytest.mark.skipif(os.name!='posix',reason='Real PTY')
def test_unattended_install_answers_only_reviewed_prompts_and_redacts_secret(tmp_path):
    import sys
    from tools.ready_card_first_boot import install
    script="input('Type INSTALL to apply this reviewed plan: ');p=input('Create a separate network administration password (12+ characters): ');q=input('Repeat password: ');assert p==q"
    password='a-private-temporary-test-password'
    install([sys.executable,'-c',script],'a'*64,password,tmp_path/'install.log')
    assert password not in (tmp_path/'install.log').read_text()
