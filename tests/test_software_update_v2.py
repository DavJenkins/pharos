import os
from pathlib import Path
from tools.software_update import allowed,digest
from tests import test_software_transaction as base

class ExtendedSoftwareTransactions(base.SoftwareTransactions):
    def helper_payload(self):
        target=self.root/'usr/local/libexec/dataark-library';target.parent.mkdir(parents=True);target.write_bytes(b'old helper');target.chmod(0o755)
        payload=self.payload/'helpers/dataark-library';payload.parent.mkdir();payload.write_bytes(b'new helper')
        return target,{'helpers/dataark-library':digest(target)}
    def test_signed_review_handles_only_exact_existing_drift(self):
        target=self.source/'app/main.py';target.write_bytes(b'reviewed local source')
        self.build(reviewed_local_files={'source/app/main.py':digest(target)})
        self.assertEqual(self.updater.apply(self.stage())['state'],'completed')
        self.preserved()
    def test_signed_review_does_not_accept_subsequent_edit(self):
        target=self.source/'app/main.py';target.write_bytes(b'reviewed local source')
        self.build(reviewed_local_files={'source/app/main.py':digest(target)})
        identifier=self.stage();target.write_bytes(b'not reviewed')
        with self.assertRaisesRegex(ValueError,'Reviewed local file changed'):self.updater.apply(identifier)
        self.assertEqual(target.read_bytes(),b'not reviewed')
    def test_unreviewed_edit_is_still_refused(self):
        (self.source/'app/main.py').write_bytes(b'unknown edit')
        self.build(reviewed_local_files={})
        with self.assertRaisesRegex(ValueError,'Local software edits'):self.stage()
    def test_helper_installs_only_with_signed_existing_hash(self):
        target,review=self.helper_payload();self.build(reviewed_local_files=review)
        self.assertEqual(self.updater.apply(self.stage())['state'],'completed')
        self.assertEqual(target.read_bytes(),b'new helper');self.assertEqual(target.stat().st_mode&0o777,0o755)
        self.preserved()
    def test_helper_rollback_restores_exact_bytes_and_mode(self):
        target,review=self.helper_payload();self.build(reviewed_local_files=review);self.updater.runtime=base.Runtime((False,True))
        self.assertEqual(self.updater.apply(self.stage())['state'],'rolled_back')
        self.assertEqual(target.read_bytes(),b'old helper');self.assertEqual(target.stat().st_mode&0o777,0o755)
        self.assertNotIn('helpers/dataark-library',self.updater.receipt()['files'])
    def test_system_unit_changes_reload_and_rollback(self):
        name='systemd/dataark-wifi-roles.service';target=self.updater.destination(name);target.parent.mkdir(parents=True);target.write_bytes(b'old unit')
        payload=self.payload/name;payload.parent.mkdir();payload.write_bytes(b'new unit')
        self.build(reviewed_local_files={name:digest(target)})
        runtime=base.Runtime((False,True));runtime.reload_units=lambda:runtime.calls.append('reload')
        self.updater.runtime=runtime
        self.assertEqual(self.updater.apply(self.stage())['state'],'rolled_back')
        self.assertEqual(runtime.calls.count('reload'),2);self.assertEqual(target.read_bytes(),b'old unit')
    def test_privileged_scope_excludes_credentials_and_unregistered_units(self):
        for name in ['helpers/shell','helpers/../../etc/shadow','systemd/sshd.service','systemd/dataark-evil.service','source/config/secrets.py','web/index.html']:
            with self.subTest(name=name):self.assertFalse(allowed(name))

    def test_publication_failure_restores_generated_recipient_pages(self):
        template=self.source/'app/templates/index.html';template.parent.mkdir(parents=True);template.write_bytes(b'old template')
        payload=self.payload/'source/app/templates/index.html';payload.parent.mkdir(parents=True);payload.write_bytes(b'new template')
        for target in self.updater.publication_files():target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b'recipient-specific page')
        self.build(reviewed_local_files={'source/app/templates/index.html':digest(template)})
        runtime=base.Runtime((False,True))
        def publish():
            for target in self.updater.publication_files():target.write_bytes(b'new generated page')
        runtime.publish=publish;self.updater.runtime=runtime
        self.assertEqual(self.updater.apply(self.stage())['state'],'rolled_back')
        for target in self.updater.publication_files():self.assertEqual(target.read_bytes(),b'recipient-specific page')
        self.assertEqual(template.read_bytes(),b'old template')

    def test_initial_enrollment_covers_tools_helpers_units_and_public_pages(self):
        from tools.software_update import Updater
        root=self.root/'fresh';u=Updater(root,base.Runtime())
        for name in ['source/tools/example.py','source/app/templates/index.html','source/app/static/library.html','web/library.html','helpers/dataark-library','systemd/dataark-wifi-roles.service']:
            target=u.destination(name);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b'initial software')
        u.enroll('c'*40,'test-lan')
        self.assertEqual(len(u.receipt()['files']),6)
        with self.assertRaisesRegex(ValueError,'Already enrolled'):u.enroll('d'*40,'test-lan')

    def test_format_one_cannot_acquire_extended_privileged_scope(self):
        import json,subprocess
        target,review=self.helper_payload();self.build(reviewed_local_files=review)
        folder=self.updater.stage_path(self.stage());manifest=folder/'manifest.json'
        value=json.loads(manifest.read_text());value['schema']=1;value.pop('reviewed_local_files');manifest.write_text(json.dumps(value))
        subprocess.run(['/usr/bin/openssl','pkeyutl','-sign','-inkey',str(self.key),'-rawin','-in',str(manifest),'-out',str(folder/'manifest.sig')],check=True,capture_output=True)
        with self.assertRaisesRegex(ValueError,'requires schema 2|require schema 2'):self.updater.validate(folder)
