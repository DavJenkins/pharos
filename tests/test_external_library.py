import json
from pathlib import Path
import pytest
from tools import external_library as x

def test_copy_is_verified_and_source_is_retained(tmp_path):
    source=tmp_path/'source';target=tmp_path/'target';source.mkdir();target.mkdir()
    (source/'books').mkdir();(source/'books/one.pdf').write_bytes(b'book'*4096)
    before=x.digest(source/'books/one.pdf');progress=[]
    x.copy_verified(source,target,x.files(source),lambda:None,lambda n,t:progress.append((n,t)))
    assert x.digest(target/'books/one.pdf')==before==x.digest(source/'books/one.pdf')
    assert progress==[(1,1)]
    assert not list(target.rglob('*.dataark-copying'))

def test_source_change_requires_new_review(tmp_path):
    source=tmp_path/'source';target=tmp_path/'target';source.mkdir();target.mkdir()
    (source/'book').write_bytes(b'old');entries=x.files(source);(source/'book').write_bytes(b'new edition')
    with pytest.raises(ValueError,match='Source changed'):x.copy_verified(source,target,entries,lambda:None,lambda *_:None)
    assert not (target/'book').exists()

def test_disconnect_aborts_before_publishing_file(tmp_path):
    source=tmp_path/'source';target=tmp_path/'target';source.mkdir();target.mkdir();(source/'book').write_bytes(b'book')
    calls=[]
    def guard():
        calls.append(1)
        if len(calls)>1:raise ValueError('disconnected')
    with pytest.raises(ValueError,match='disconnected'):x.copy_verified(source,target,x.files(source),guard,lambda *_:None)
    assert not (target/'book').exists()
    assert (source/'book').read_bytes()==b'book'

def test_bad_checksum_cannot_publish(tmp_path,monkeypatch):
    source=tmp_path/'source';target=tmp_path/'target';source.mkdir();target.mkdir();(source/'book').write_bytes(b'book')
    monkeypatch.setattr(x,'digest',lambda p:'bad' if p.name.endswith('copying') else 'good')
    with pytest.raises(ValueError,match='verification failed'):x.copy_verified(source,target,x.files(source),lambda:None,lambda *_:None)
    assert not (target/'book').exists()

@pytest.mark.parametrize('uuid',['../../etc/passwd','a b','$(reboot)','',None])
def test_only_uuid_values_allowed(uuid):
    with pytest.raises(ValueError):x.uuid_ok(uuid)

def test_fstab_retains_os_mounts_and_makes_external_optional():
    original='UUID=system / ext4 defaults 0 1\n/var/lib/dataark/demo-library.ext4 /mnt/storage ext4 loop,nofail 0 0\n'
    result=x.fstab_external(original,'ABCD-1234','exfat')
    assert 'UUID=system / ext4 defaults 0 1' in result
    assert 'demo-library.ext4' not in result
    assert result.count(' /mnt/storage ')==1
    assert 'nofail' in result and 'uid=1000' in result and 'device-timeout=10s' in result

def test_ambiguous_mount_config_refused():
    with pytest.raises(ValueError,match='exactly one'):x.fstab_external('UUID=a / ext4 defaults 0 1\n','ABCD-1234','ext4')

def test_system_disk_not_offered_even_when_usb(monkeypatch):
    raw={'blockdevices':[{'path':'/dev/sda','tran':'usb','children':[{'path':'/dev/sda1','type':'part','fstype':'ext4','uuid':'abcd-1234','mountpoints':['/']}]},
                         {'path':'/dev/sdb','tran':'usb','model':'Spare','children':[{'path':'/dev/sdb1','type':'part','fstype':'ext4','uuid':'abcd-5678','size':123,'mountpoints':[]}]}]}
    def lsblk(args):
        # Without NAME or --tree, lsblk JSON does not nest partition children.
        if '--tree' not in args:return json.dumps({'blockdevices':[dict(d,children=[]) for d in raw['blockdevices']]})
        return json.dumps(raw)
    monkeypatch.setattr(x,'run',lsblk)
    assert [d['uuid'] for d in x.devices()]==['abcd-5678']

def test_nonempty_drive_not_adopted(tmp_path,monkeypatch):
    (tmp_path/'personal.txt').write_text('keep me')
    monkeypatch.setattr(x,'source_identity',lambda:1);monkeypatch.setattr(x,'mounted',lambda _:({'uuid':'abcd-1234'},tmp_path));monkeypatch.setattr(x,'files',lambda _:[])
    with pytest.raises(ValueError,match='empty formatted drive'):x.plan('abcd-1234')
    assert (tmp_path/'personal.txt').read_text()=='keep me'

def test_insufficient_space_keeps_source_and_target(tmp_path,monkeypatch):
    monkeypatch.setattr(x,'source_identity',lambda:1)
    monkeypatch.setattr(x,'mounted',lambda _:({'uuid':'abcd-1234'},tmp_path))
    monkeypatch.setattr(x,'files',lambda _:[{'path':'large','bytes':3*1024**3,'mtime':1}])
    monkeypatch.setattr(x.shutil,'disk_usage',lambda _:type('Usage',(),{'free':1024**3})())
    with pytest.raises(ValueError,match='whole library'):x.plan('abcd-1234')
    assert list(tmp_path.iterdir())==[]


def test_regenerated_usage_does_not_invalidate_collection_preview(tmp_path):
    (tmp_path/'book.pdf').write_bytes(b'book')
    (tmp_path/'usage.json').write_text('old activity')
    before=x.files(tmp_path)
    (tmp_path/'usage.json').write_text('new activity with changed size')
    (tmp_path/'usage.tmp').write_text('atomic export in progress')
    assert x.files(tmp_path)==before
    assert [item['path'] for item in before]==['book.pdf']
    (tmp_path/'book.pdf').write_bytes(b'new edition')
    assert x.files(tmp_path)!=before


def test_usage_named_content_in_a_collection_is_still_copied(tmp_path):
    (tmp_path/'manuals').mkdir()
    (tmp_path/'manuals/usage.json').write_text('publication data')
    assert [item['path'] for item in x.files(tmp_path)]==['manuals/usage.json']


def test_non_posix_copy_verifies_bytes_without_chmod_or_chown(tmp_path,monkeypatch):
    source=tmp_path/'source';target=tmp_path/'target';source.mkdir();target.mkdir()
    (source/'book.pdf').write_bytes(b'book data')
    entries=x.files(source)
    def forbidden(*args,**kwargs):raise AssertionError('exFAT has no Unix ownership/mode metadata')
    monkeypatch.setattr(Path,'chmod',forbidden)
    monkeypatch.setattr(x.os,'chown',forbidden,raising=False)
    x.copy_verified(source,target,entries,lambda:None,lambda *_:None,posix_permissions=False)
    assert (target/'book.pdf').read_bytes()==(source/'book.pdf').read_bytes()


def test_portable_mount_requires_ownership_and_distinct_file_directory_masks():
    assert x.portable_permissions('rw,uid=1000,gid=1000,fmask=0133,dmask=0022')
    assert not x.portable_permissions('rw,fmask=0022,dmask=0022')
    assert not x.portable_permissions('rw,uid=1000,gid=1000,fmask=0022,dmask=0022')


def test_existing_portable_mount_is_reopened_instead_of_remounted(tmp_path,monkeypatch):
    row={'uuid':'ABCD-1234','device':'/dev/sda1','filesystem':'exfat','mounts':[str(tmp_path)]}
    monkeypatch.setattr(x,'devices',lambda:[row])
    monkeypatch.setattr(Path,'is_mount',lambda _:True)
    calls=[];reads=[]
    def run(args):
        calls.append(args)
        if args[0]=='findmnt':
            reads.append(True)
            return 'rw,fmask=0022,dmask=0022' if len(reads)==1 else 'rw,uid=1000,gid=1000,fmask=0133,dmask=0022'
        return ''
    monkeypatch.setattr(x,'run',run)
    assert x.mounted('ABCD-1234')[1]==tmp_path
    assert ['umount',str(tmp_path)] in calls
    assert any(a[0]=='mount' and 'remount' not in a[2] and 'fmask=0133' in a[2] for a in calls)


def test_switch_verification_survives_public_status_becoming_queued(tmp_path,monkeypatch):
    monkeypatch.setattr(x,'PRIVATE',tmp_path)
    (tmp_path/'verified.json').write_text(json.dumps({'plan_id':'reviewed-copy'}))
    (tmp_path/'status.json').write_text(json.dumps({'phase':'queued'}))
    x.require_verified({'plan_id':'reviewed-copy'})
    with pytest.raises(ValueError,match='Finish verification'):
        x.require_verified({'plan_id':'different-copy'})
    (tmp_path/'verified.json').unlink()
    with pytest.raises(ValueError,match='Finish verification'):
        x.require_verified({'plan_id':'reviewed-copy'})
