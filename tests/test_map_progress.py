import json,tempfile,unittest
from pathlib import Path
from app.services.update_status import map_progress
class ProgressTests(unittest.TestCase):
 def test_transfer_preparation_verification_and_completion(self):
  with tempfile.TemporaryDirectory() as tmp:
   state=Path(tmp)/'state.json';log=Path(tmp)/'log';state.write_text(json.dumps({'state':'downloading'}));log.write_text('fetching chunks   0% | (0 B/20 GB)')
   self.assertEqual(map_progress(state,log,True)['label'],'Preparing U.S. offline map')
   log.write_text('fetching chunks  1%\rfetching chunks  37% | data')
   self.assertEqual(map_progress(state,log,True)['percent'],37)
   state.write_text(json.dumps({'state':'verifying'}));self.assertEqual(map_progress(state,log,True)['state'],'verifying')
   state.write_text(json.dumps({'state':'published'}));self.assertIsNone(map_progress(state,log,False))
 def test_interrupted_and_bad_status(self):
  with tempfile.TemporaryDirectory() as tmp:
   state=Path(tmp)/'state.json';log=Path(tmp)/'log';state.write_text(json.dumps({'state':'downloading'}));log.write_text('')
   self.assertEqual(map_progress(state,log,False)['state'],'error')
   state.write_text('broken');self.assertIsNone(map_progress(state,log,True))
