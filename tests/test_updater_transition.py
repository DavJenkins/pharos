import hashlib,json,os,subprocess,tempfile,unittest
from pathlib import Path
from tools.transition_software_updater import transition

@unittest.skipUnless(os.geteuid()==0,'Transition ownership checks require root in an isolated fixture')
class VerifierTransition(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  self.state=self.root/'var/lib/dataark-software-updates';self.state.mkdir(parents=True)
  self.target=self.root/'usr/local/libexec/software_update.py';self.target.parent.mkdir(parents=True);self.target.write_bytes(b'# old verifier')
  self.receipt=self.state/'installed.json';self.receipt.write_bytes(b'{"revision":"original"}')
  keys=self.root/'etc/dataark/software-update-keys';keys.mkdir(parents=True)
  self.key=self.root/'private.pem';self.pub=keys/'release.pem'
  subprocess.run(['/usr/bin/openssl','genpkey','-algorithm','ED25519','-out',str(self.key)],check=True,capture_output=True)
  subprocess.run(['/usr/bin/openssl','pkey','-in',str(self.key),'-pubout','-out',str(self.pub)],check=True,capture_output=True)
  self.engine=self.root/'new.py';self.engine.write_bytes(b'def allowed(name): return name == "helpers/dataark-library"\n')
  sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
  self.manifest=self.root/'manifest.json';self.manifest.write_text(json.dumps({'schema':1,'type':'updater-v2-transition','from_engine_sha256':sha(self.target),'to_engine_sha256':sha(self.engine),'receipt_sha256':sha(self.receipt)}))
  self.signature=self.root/'manifest.sig'
  subprocess.run(['/usr/bin/openssl','pkeyutl','-sign','-inkey',str(self.key),'-rawin','-in',str(self.manifest),'-out',str(self.signature)],check=True,capture_output=True)
 def run_transition(self):return transition(self.engine,self.manifest,self.signature,self.root)
 def test_preserves_receipt_and_keeps_old_verifier(self):
  before=self.receipt.read_bytes();result=self.run_transition()
  self.assertEqual(result['state'],'completed');self.assertEqual(self.receipt.read_bytes(),before)
  self.assertEqual((Path(result['backup'])/'software_update.py').read_bytes(),b'# old verifier')
 def test_changed_engine_is_rejected_before_replacement(self):
  self.engine.write_bytes(b'# altered')
  with self.assertRaisesRegex(ValueError,'baseline changed'):self.run_transition()
  self.assertEqual(self.target.read_bytes(),b'# old verifier')
 def test_untrusted_signature_is_rejected(self):
  self.signature.write_bytes(b'x'*64)
  with self.assertRaisesRegex(ValueError,'not trusted'):self.run_transition()
  self.assertEqual(self.target.read_bytes(),b'# old verifier')
 def test_queued_update_blocks_transition(self):
  (self.state/'queued.json').write_text('{}')
  with self.assertRaisesRegex(ValueError,'queued'):self.run_transition()
 def test_bad_new_verifier_restores_old_verifier(self):
  self.engine.write_bytes(b'raise RuntimeError("import failure")\n')
  value=json.loads(self.manifest.read_text());value['to_engine_sha256']=hashlib.sha256(self.engine.read_bytes()).hexdigest();self.manifest.write_text(json.dumps(value))
  subprocess.run(['/usr/bin/openssl','pkeyutl','-sign','-inkey',str(self.key),'-rawin','-in',str(self.manifest),'-out',str(self.signature)],check=True,capture_output=True)
  with self.assertRaisesRegex(ValueError,'import check'):self.run_transition()
  self.assertEqual(self.target.read_bytes(),b'# old verifier')
