import json
import tempfile
import unittest
from unittest.mock import patch
from app.services import integration_health as health

def base():
    return {'status':{'state':'ok','issues':[],'update':None}, 'services':{'fastapi':'running'}}

class IntegrationHealthTests(unittest.TestCase):
    def test_successful_software_update_changes_fingerprint_without_warning(self):
        with patch.object(health,'get_status',return_value=base()),patch.object(health,'public_status',return_value={}),patch.object(health,'failed_units',return_value=[]),patch.object(health,'REFERENCE',self.root/'missing'),patch('app.services.software_installation.status') as software:
            software.return_value={'state':'completed','revision':'a','sequence':1};first=health.collect()
            software.return_value={'state':'completed','revision':'b','sequence':2};second=health.collect()
        self.assertEqual(first['state'],'ok');self.assertEqual(second['state'],'ok');self.assertNotEqual(first['fingerprint'],second['fingerprint'])
    def setUp(self):
        p=patch('app.services.software_installation.status',return_value={'state':'not_installed'});p.start();self.addCleanup(p.stop)
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        from pathlib import Path
        self.root=Path(self.temp.name)

    def test_certificate_expiry_and_stable_fingerprint(self):
        tmp_path=self.root
        path=tmp_path/'sources.json'
        path.write_text(json.dumps({'sources':{'a':{'status':'error'},'b':{'pending_change':True}}}))
        with patch.object(health,'get_status',return_value=base()), patch.object(health,'public_status',return_value={'certificate_health':'expired'}), patch.object(health,'failed_units',return_value=['x11vnc.service']), patch.object(health,'REFERENCE',path):
            first=health.collect(); second=health.collect()
        assert first['state']=='error'
        assert first['fingerprint']==second['fingerprint']
        assert {p['id'] for p in first['problems']}=={'https.certificate','service.x11vnc.service','content.source_checks','content.source_changes'}
        assert first['source_checks']['errors']==1

    def test_optional_https_and_absent_checks_are_not_failures(self):
        tmp_path=self.root
        with patch.object(health,'get_status',return_value=base()), patch.object(health,'public_status',return_value={'phase':'not_configured'}), patch.object(health,'failed_units',return_value=[]), patch.object(health,'REFERENCE',tmp_path/'missing'):
            value=health.collect()
        assert value['state']=='ok'
        assert value['problem_count']==0

    def test_map_failure_is_reported_and_recovery_changes_fingerprint(self):
        tmp_path=self.root
        current=base(); current['status']['update']={'state':'error','label':'Map update needs attention'}
        with patch.object(health,'get_status',return_value=current), patch.object(health,'public_status',return_value={}), patch.object(health,'failed_units',return_value=[]), patch.object(health,'REFERENCE',tmp_path/'missing'):
            failed=health.collect()
            current['status']['update']=None
            recovered=health.collect()
        assert failed['problems'][0]['id']=='content.update_failed'
        assert failed['fingerprint']!=recovered['fingerprint']
