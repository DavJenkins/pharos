import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools import prepare_recipient as r

class RecipientTests(unittest.TestCase):
    def fixture(self,root):
        for relative in ('etc/dataark','etc/ssh','home/admin/.ssh','root/.ssh','var/lib/dataark','etc/cloud/cloud.cfg.d','boot/firmware'):
            (root/relative).mkdir(parents=True,exist_ok=True)
        (root/'etc/dataark-physical-bootstrap-test').write_text('test')
        (root/'etc/hosts').write_text('127.0.0.1 localhost\n127.0.1.1 test-host\n')
        (root/'etc/machine-id').write_text('old')
        (root/'var/lib/dataark/demo-library.json').write_text(json.dumps({'stage':'ready'}))
        (root/'etc/dataark/network-admin.json').write_text('{"hash":"old"}')
        (root/'etc/ssh/ssh_host_ed25519_key').write_text('old-private')
        (root/'home/admin/.ssh/authorized_keys').write_text('provisioner')
        (root/'root/.ssh/authorized_keys').write_text('provisioner')
        (root/'boot/firmware/user-data').write_text('ssh_authorized_keys: [provisioner]')
        content=root/'mnt/storage/book';content.parent.mkdir(parents=True);content.write_bytes(b'preserved knowledge')
        return content

    def test_arming_preserves_running_identity_then_boot_replaces_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);content=self.fixture(root)
            r.arm(root)
            self.assertEqual((root/'etc/machine-id').read_text(),'old')
            self.assertTrue((root/'home/admin/.ssh/authorized_keys').exists())
            r.first_boot(root)
            state=json.loads((root/'var/lib/dataark/recipient.json').read_text())
            self.assertEqual(state['state'],'awaiting_local_password')
            self.assertEqual(len(state['machine_id']),32)
            self.assertTrue(state['hostname'].startswith('dataark-'))
            self.assertFalse((root/'etc/ssh/ssh_host_ed25519_key').exists())
            self.assertFalse((root/'home/admin/.ssh/authorized_keys').exists())
            self.assertFalse((root/'root/.ssh/authorized_keys').exists())
            self.assertNotIn('provisioner',(root/'boot/firmware/user-data').read_text())
            self.assertEqual(content.read_bytes(),b'preserved knowledge')
            self.assertEqual(json.loads((root/'etc/dataark/device-identity.json').read_text())['device_id'],state['device_id'])
            r.first_boot(root)
            self.assertEqual(json.loads((root/'var/lib/dataark/recipient.json').read_text()),state)

    def test_hotspot_enrollment_rejects_wrong_code_and_consumes_correct_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root);r.arm(root)
            code=(root/'root/dataark-recipient-setup-code').read_text().strip()
            self.assertRegex(code,r'^[0-9]{4}$')
            r.first_boot(root)
            with self.assertRaisesRegex(ValueError,'code not accepted'):r.enroll({'code':'wrong','password':'a long new password','admin_password':'a different long password'},root)
            self.assertEqual(r.enroll({'code':code,'password':'a long new password','admin_password':'a different long password'},root)['state'],'ready')
            self.assertFalse((root/'var/lib/dataark/recipient-enrollment.json').exists())
            self.assertFalse((root/'root/dataark-recipient-setup-code').exists())
            with self.assertRaisesRegex(ValueError,'not pending'):r.enroll({'code':code,'password':'another long password','admin_password':'a different long password'},root)

    def test_five_failures_pause_even_correct_code_then_allow_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root);r.arm(root);r.first_boot(root)
            code=(root/'root/dataark-recipient-setup-code').read_text().strip()
            data={'code':code,'password':'a long new password','admin_password':'a different long password'}
            wrong={**data,'code':'0000' if code!='0000' else '0001'}
            with patch.object(r.time,'time',return_value=1000):
                for _ in range(5):
                    with self.assertRaisesRegex(ValueError,'not accepted'):r.enroll(wrong,root)
                with self.assertRaisesRegex(ValueError,'Wait one minute'):r.enroll(data,root)
            with patch.object(r.time,'time',return_value=1061):
                self.assertTrue(r.enroll(data,root)['ok'])

    def test_pairing_code_preserves_leading_zeroes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            with patch.object(r.secrets,'randbelow',return_value=7):r.arm(root)
            self.assertEqual((root/'root/dataark-recipient-setup-code').read_text().strip(),'0007')

    def test_refuses_general_appliance_and_integrations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            (root/'etc/dataark/bugout-ha.json').write_text('{"token":"private"}')
            with self.assertRaisesRegex(ValueError,'integration'):r.arm(root)
            (root/'etc/dataark/bugout-ha.json').unlink()
            (root/'etc/dataark-physical-bootstrap-test').unlink()
            with self.assertRaisesRegex(ValueError,'demonstration'):r.arm(root)

    def test_identity_precedes_https_reconciliation(self):
        self.assertIn('dataark-https-reconcile.service',r.UNIT.split('Before=')[1].splitlines()[0])

    def test_certificate_added_after_arming_blocks_identity_replacement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root);r.arm(root)
            active=root/'etc/dataark/https/active.json';active.parent.mkdir();active.write_text('{"domain":"ark.owner-domain.org"}')
            with self.assertRaisesRegex(ValueError,'certificate'):r.first_boot(root)
            self.assertEqual((root/'etc/machine-id').read_text(),'old')
            self.assertTrue((root/'var/lib/dataark/recipient-armed').exists())

    def test_password_minimum_and_unique_salts(self):
        with self.assertRaises(ValueError):r.password_record('short')
        a=r.password_record('a sufficiently long phrase');b=r.password_record('a sufficiently long phrase')
        self.assertNotEqual(a['hash'],b['hash'])

if __name__=='__main__':unittest.main()
