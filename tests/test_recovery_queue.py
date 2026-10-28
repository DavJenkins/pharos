import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import yaml
from tools import recovery_queue as q
from tools import content_profile as content

GIB=1024**3
POLICY={'schema':1,'reserve_gib':10,'minimal_file_max_bytes':16*1024**2,
        'recommended_archives':['small-zim'],'recipe_tiers':{'radio-study':'minimal','family':'recommended','forms':'recommended'}}

class QueueFixtures:
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);self.profile=self.root/'content.yaml';self.state=self.root/'state'
  self.c={'schema':1,'reserve_gib':10,'content_root':str(self.root),'manifest':'public-manifest.yaml',
          'archives':[{'id':'huge','path':'huge.zim','url':'https://example.org/huge.zim','bytes':100*GIB}],
          'direct_files':[{'id':'useful','path':'preparedness/guide.pdf','url':'https://example.org/guide.pdf','bytes':10}],
          'recipes':[{'id':'indexes','installed_bytes':0,'temporary_bytes':0,'update_headroom_bytes':0}]}
  (self.root/'public-manifest.yaml').write_text('assets: []\n');self.write()
 def write(self):self.profile.write_text(yaml.safe_dump(self.c))
 def plan(self,preset='full',free=1000*GIB):return q.build_plan(self.profile,preset,POLICY,free)
 def create(self,preset='full'):
  plan=self.plan(preset);return q.create(plan,plan['plan_id'],self.state)
 def run_queue(self,runner=lambda *args:0,restart=False):
  with patch.object(q.shutil,'disk_usage',return_value=type('Usage',(),{'free':1000*GIB})()):return q.run(self.state,restart,runner)

class QueueTests(QueueFixtures,unittest.TestCase):
 def test_none_has_no_jobs_or_capacity_requirement(self):
  p=self.plan('none',0);self.assertTrue(p['capacity']['fits']);self.assertFalse(p['jobs']);self.assertEqual(p['capacity']['required_free_bytes'],0)
 def test_small_independent_content_precedes_huge_archive_and_indexes_last(self):
  self.assertEqual([j['id'] for j in self.plan()['jobs']],['useful','huge','indexes'])
 def test_minimal_excludes_large_archives_and_disabled_choices(self):
  self.c['direct_files'].append({'id':'removed','enabled':False,'path':'preparedness/removed.pdf','url':'https://example.org/a.pdf','bytes':1});self.write()
  self.assertEqual([j['id'] for j in self.plan('minimal')['jobs']],['useful','indexes'])
 def test_capacity_counts_staging_update_headroom_and_reserve(self):
  p=self.plan();cap=p['capacity'];self.assertGreater(cap['required_free_bytes'],200*GIB)
  self.assertFalse(self.plan(free=100*GIB)['capacity']['fits'])
 def test_unknown_size_blocks_full_but_not_none(self):
  self.c['archives'][0].pop('bytes');self.write()
  self.assertEqual(self.plan()['capacity']['unknown_packages'],['huge']);self.assertFalse(self.plan()['capacity']['fits']);self.assertTrue(self.plan('none',0)['capacity']['fits'])
 def test_dependency_closure_and_topological_order(self):
  self.c['recipes'] += [{'id':'family','requires':['forms'],'installed_bytes':1},{'id':'forms','requires':['radio-study'],'installed_bytes':50},{'id':'radio-study','installed_bytes':100}];self.write()
  ids=[j['id'] for j in self.plan('recommended')['jobs']]
  self.assertLess(ids.index('radio-study'),ids.index('forms'));self.assertLess(ids.index('forms'),ids.index('family'))
 def test_dependency_cycle_and_disabled_dependency_rejected(self):
  self.c['recipes'] += [{'id':'family','requires':['forms'],'installed_bytes':1},{'id':'forms','requires':['family'],'installed_bytes':1}];self.write()
  with self.assertRaises(ValueError):self.plan('recommended')
  self.c['recipes'][-1]['enabled']=False;self.write()
  with self.assertRaises(ValueError):self.plan('recommended')
 def test_explicit_exact_approval_and_existing_queue_protection(self):
  p=self.plan()
  with self.assertRaises(ValueError):q.create(p,'wrong',self.state)
  self.assertFalse((self.state/'queue.json').exists());q.create(p,p['plan_id'],self.state)
  with self.assertRaises(ValueError):q.create(p,p['plan_id'],self.state)
 def test_plan_identity_ignores_incidental_free_space_changes(self):
  self.assertEqual(self.plan(free=1000*GIB)['plan_id'],self.plan(free=999*GIB)['plan_id'])
 def test_existing_size_only_affects_capacity_and_executor_requests_hash_verification(self):
  (self.root/'huge.zim').write_bytes(b'a');self.c['archives'][0]['bytes']=1;self.write();p=self.plan();self.assertTrue(next(j for j in p['jobs'] if j['id']=='huge')['present_for_capacity'])
  with patch.object(content,'download',return_value='present (checksum checked)') as download,patch('tools.publish_content.publish'),patch.object(q.subprocess,'run'):q.execute_job(p,p['jobs'][0],self.state);self.assertTrue(download.call_args.kwargs['verify_existing'])
 def test_resume_keeps_completed_packages_and_retries_failed_work(self):
  self.create();calls=[]
  def fail(q_,j,d):calls.append(j['id']);return 1 if j['id']=='huge' else 0
  first=self.run_queue(fail);self.assertEqual(first['status'],'needs_attention');self.assertEqual(first['jobs'][-1]['status'],'blocked')
  calls.clear();last=self.run_queue(lambda q_,j,d:calls.append(j['id']) or 0)
  self.assertEqual(calls,['huge','indexes']);self.assertEqual(last['status'],'complete')
 def test_cancel_preserves_completed_files_and_resume_retries_interrupted_package(self):
  self.create();sentinel=self.root/'keep.pdf';sentinel.write_bytes(b'verified')
  def cancel(q_,j,d):
   if j['id']=='huge':q.control('cancel',d);return 'interrupted'
   return 0
  first=self.run_queue(cancel);self.assertEqual(first['status'],'cancelled');self.assertEqual(first['jobs'][0]['status'],'complete');self.assertEqual(sentinel.read_bytes(),b'verified')
  calls=[];self.run_queue(lambda q_,j,d:calls.append(j['id']) or 0);self.assertNotIn('useful',calls)
 def test_interrupted_running_job_is_requeued_on_resume(self):
  state=self.create();state['status']='running';state['jobs'][0]['status']='running';q.save(self.state/'queue.json',state)
  self.assertEqual(self.run_queue()['status'],'complete')
 def test_profile_change_prevents_resume(self):
  self.create();self.c['reserve_gib']=20;self.write()
  with self.assertRaises(ValueError):self.run_queue()
 def test_restart_rechecks_completed_content_without_deleting(self):
  self.create();self.run_queue();calls=[];self.run_queue(lambda q_,j,d:calls.append(j['id']) or 0,True);self.assertEqual(calls,['useful','huge','indexes'])
 def test_snapshot_exposes_completed_links_and_partial_progress_only(self):
  state=self.create();state['jobs'][0]['status']='complete';q.save(self.state/'queue.json',state)
  content.staging_path(self.root,'huge.zim').write_bytes(b'partial');s=q.snapshot(self.state)
  self.assertEqual(s['jobs'][1]['partial_bytes'],7);self.assertIsNone(s['jobs'][1]['path']);self.assertEqual(s['jobs'][0]['path'],'preparedness/guide.pdf');self.assertNotIn('profile',s)
 def test_recipe_estimates_include_auxiliary_files_and_travel_with_profile(self):
  (self.root/'forms').mkdir();(self.root/'forms/book.pdf').write_bytes(b'a'*100)
  items=content.bound_recipes([{'id':'forms'},{'id':'indexes'},{'id':'curriculum'}],self.root)
  self.assertEqual(items[0]['installed_bytes'],125);self.assertEqual(items[0]['temporary_bytes'],250);self.assertEqual(items[1]['installed_bytes'],0);self.assertNotIn('installed_bytes',items[2])

if __name__=='__main__':unittest.main()

class TransitionTests(QueueFixtures,unittest.TestCase):
 def test_package_completion_does_not_finish_the_whole_queue(self):
  state=self.create();q.transition(state,self.state,'complete',state['jobs'][0])
  self.assertEqual(json.loads((self.state/'queue.json').read_text())['status'],'running')
  calls=[];self.run_queue(lambda q_,j,d:calls.append(j['id']) or 0)
  self.assertEqual(calls,['huge','indexes'])

class SharedLockTests(unittest.TestCase):
 def test_inherited_lock_is_real_and_competing_open_is_rejected(self):
  import os, subprocess, sys
  from tools.content_lock import acquire
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'lock'
   with q.lock(path) as parent, path.open('a') as other:
    with patch.dict(os.environ,{},clear=True):
     with self.assertRaises(BlockingIOError):acquire(other)
    with patch.dict(os.environ,{'DATAARK_CONTENT_LOCK_FD':str(parent.fileno())}):acquire(other)
    script="from pathlib import Path; from tools.content_lock import acquire; f=Path("+repr(str(path))+").open('a'); acquire(f)"
    env={**os.environ,'DATAARK_CONTENT_LOCK_FD':str(parent.fileno()),'PYTHONPATH':str(q.ROOT)}
    subprocess.run([sys.executable,'-c',script],env=env,pass_fds=(parent.fileno(),),check=True)
 def test_invalid_inherited_descriptor_does_not_bypass_lock(self):
  import os
  from tools.content_lock import acquire
  with tempfile.TemporaryDirectory() as tmp:
   with (Path(tmp)/'a').open('a') as a,(Path(tmp)/'b').open('a') as b:
    with patch.dict(os.environ,{'DATAARK_CONTENT_LOCK_FD':str(a.fileno())}):
     with self.assertRaises(ValueError):acquire(b)

class RealWorkerTests(QueueFixtures,unittest.TestCase):
 def test_subprocess_restores_and_verifies_fixture_without_network(self):
  import os
  c=copy.deepcopy(self.c);c['archives']=[];c['recipes']=[];c['direct_files'][0]['sha256']=hashlib.sha256(b'0123456789').hexdigest();self.c=c;self.write();self.create('minimal')
  bindir=self.root/'bin';bindir.mkdir();curl=bindir/'curl';curl.write_text("#!/usr/bin/python3\nimport sys\nfrom pathlib import Path\nPath(sys.argv[sys.argv.index('--output')+1]).write_bytes(b'0123456789')\n");curl.chmod(0o755)
  with q.lock(self.root/'fake-worker.lock') as held,patch.dict(os.environ,{'PATH':str(bindir)+os.pathsep+os.environ['PATH'],'DATAARK_CONTENT_LOCK_FD':str(held.fileno())}):
   result=self.run_queue(q.child)
  self.assertEqual(result['status'],'complete',(self.state/'worker.log').read_text());self.assertEqual((self.root/'preparedness/guide.pdf').read_bytes(),b'0123456789');self.assertEqual((self.root/'.dataark-restoration').stat().st_mode&0o777,0o700)
 def test_real_cancel_terminates_download_and_preserves_partial(self):
  import os,threading,time
  self.c['archives']=[];self.c['recipes']=[];self.write();self.create('minimal')
  bindir=self.root/'bin';bindir.mkdir();curl=bindir/'curl';curl.write_text("#!/usr/bin/python3\nimport sys,time\nfrom pathlib import Path\nPath(sys.argv[sys.argv.index('--output')+1]).write_bytes(b'part')\ntime.sleep(60)\n");curl.chmod(0o755)
  def cancel():
   for _ in range(100):
    if list((self.root/'.dataark-restoration').glob('*.part')):break
    time.sleep(.05)
   q.control('cancel',self.state)
  thread=threading.Thread(target=cancel)
  with q.lock(self.root/'fake-worker.lock') as held,patch.dict(os.environ,{'PATH':str(bindir)+os.pathsep+os.environ['PATH'],'DATAARK_CONTENT_LOCK_FD':str(held.fileno())}):
   thread.start();result=self.run_queue(q.child);thread.join()
  self.assertEqual(result['status'],'cancelled',(self.state/'worker.log').read_text());self.assertFalse((self.root/'preparedness/guide.pdf').exists());self.assertTrue(content.staging_path(self.root,'preparedness/guide.pdf').exists())
