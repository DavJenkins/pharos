import unittest
from unittest.mock import patch
from app.services import software_updates as service

CURRENT='a'*40
TARGET='b'*40

def release(tag,preview=False):
    return {'tag_name':tag,'prerelease':preview,'draft':False,'target_commitish':TARGET,'published_at':'2026-10-29T00:00:00Z','assets':[{'name':'data-ark-'+tag+'.tar.gz','state':'uploaded'}]}

class SoftwareUpdateTests(unittest.TestCase):
    def setUp(self):
        service.CACHE.clear()
        p=patch('app.services.software_installation.status',return_value={'ok':False});p.start();self.addCleanup(p.stop)
    def test_filter_documentation_drafts_and_preview(self):
        stable=release('bootstrap-2026.10.28');preview=release('bootstrap-2026.10.29-preview.1',True);draft=release('bootstrap-2026.10.30');draft['draft']=True
        data=[{'tag_name':'documentation-2026.10.29'},preview,draft,stable]
        self.assertEqual(service.candidates(data),[stable])
        self.assertEqual(service.candidates(data,True),[preview,stable])
    def test_release_needs_actual_package_and_tag(self):
        item=release('bootstrap-2026.10.29');item['assets']=[]
        self.assertEqual(service.candidates([item,release('bootstrap-../../evil')]),[])
    def test_signed_software_release_is_distinct_from_bootstrap(self):
        software=release('software-2026.10.29');bootstrap=release('bootstrap-2026.10.29')
        self.assertEqual(service.candidates([bootstrap,software])[0],software)
        with patch.object(service,'read_releases',return_value=[software]),patch.object(service,'relationship',return_value='newer_release'):
            result=service.check();self.assertTrue(result['installation_supported']);self.assertNotIn('not an in-place update',result['message'])
    def test_equal_unknown_and_ancestor_comparison(self):
        self.assertEqual(service.relationship(CURRENT,CURRENT),'same')
        self.assertEqual(service.relationship('main',TARGET),'uncompared')
        with patch.object(service.subprocess,'run') as run:
            run.return_value.returncode=0
            self.assertEqual(service.relationship(CURRENT,TARGET),'development_ahead')
            self.assertEqual(run.call_args.args[0][-2:],[TARGET,CURRENT])
    def test_cached_check_no_download_and_ahead_not_upgrade(self):
        with patch.object(service,'installed',return_value={'revision':CURRENT}),patch.object(service,'read_releases',return_value=[release('bootstrap-2026.10.29')]) as read,patch.object(service,'relationship',return_value='development_ahead'):
            first=service.check();self.assertEqual(first['state'],'development_ahead');self.assertFalse(first['installation_supported'])
            self.assertIs(service.check(),first);read.assert_called_once()
    def test_offline_is_not_up_to_date(self):
        with patch.object(service,'read_releases',side_effect=OSError('offline')):
            self.assertEqual(service.check()['state'],'unavailable')
    def test_preview_opt_in_and_no_stable(self):
        with patch.object(service,'read_releases',return_value=[release('bootstrap-2026.10.29-preview.1',True)]),patch.object(service,'relationship',return_value='uncompared'):
            self.assertEqual(service.check()['state'],'no_release')
            self.assertEqual(service.check(True)['state'],'uncompared')

if __name__=='__main__':unittest.main()
