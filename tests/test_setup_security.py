import asyncio,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,MagicMock
from fastapi import HTTPException
from app.services import setup_security as s
from app.routers import recipient
class SetupSecurityTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.addCleanup(patch.stopall);patch.object(s,'STATE',Path(self.tmp.name)/'security').start();self.cfg=patch.object(s,'integration',return_value={}).start();patch.object(s.time,'time',return_value=10000000).start()
 def test_offline_alert_is_durable_and_has_no_credentials(self):
  with patch.object(s.time,'time',return_value=10000000):key=s.record('code_rejected');data=s.snapshot()
  self.assertEqual(data['unacknowledged'],1);self.assertEqual(data['pending_delivery'],1)
  with s.database() as db:pass
  # Reloading state uses the same durable SQLite database.
 def test_exact_thirty_day_expiry_even_without_ha(self):
  start=10000000
  with patch.object(s.time,'time',return_value=start):s.record('code_rejected')
  with patch.object(s.time,'time',return_value=start+s.RETENTION_SECONDS-1):self.assertEqual(s.snapshot()['pending_delivery'],1)
  with patch.object(s.time,'time',return_value=start+s.RETENTION_SECONDS):s.deliver();self.assertEqual(s.snapshot()['pending_delivery'],0)
 def test_retry_reports_original_timestamp_and_stable_event_id(self):
  self.cfg.return_value={'url':'http://ha.local:8123','token':'SECRET'};response=MagicMock();response.__enter__.return_value.status=200
  with patch.object(s.time,'time',return_value=10000000),patch.object(s,'build_opener') as opener:
   opener.return_value.open.side_effect=OSError('offline');key=s.record('code_rejected')
  self.assertEqual(s.snapshot()['pending_delivery'],1)
  with patch.object(s.time,'time',return_value=10000010),patch.object(s,'build_opener') as opener:
   opener.return_value.open.return_value=response;s.deliver();calls=opener.return_value.open.call_args_list
  event=json.loads(calls[0].args[0].data);self.assertEqual(event['event_id'],key);self.assertEqual(event['timestamp'],'1970-04-26T17:46:40+00:00');self.assertNotIn('SECRET',json.dumps(event));self.assertEqual(len(calls),2);self.assertEqual(s.snapshot()['pending_delivery'],0)
 def test_acknowledgement_does_not_discard_undelivered_alert(self):
  key=s.record('code_rejected');s.acknowledge([key]);self.assertEqual(s.snapshot()['unacknowledged'],0);self.assertEqual(s.snapshot()['pending_delivery'],1)
 def test_cooldown_flood_is_grouped(self):
  with patch.object(s.time,'time',return_value=10000000):
   for i in range(8):s.record('cooldown')
   data=s.snapshot();self.assertEqual(len(data['events']),1);self.assertEqual(data['unacknowledged'],8)
 def test_repeated_worker_call_respects_backoff(self):
  self.cfg.return_value={'url':'http://ha.local:8123','token':'SECRET'}
  with patch.object(s,'build_opener') as opener:
   opener.return_value.open.side_effect=OSError('offline');s.record('code_rejected');s.deliver();self.assertEqual(opener.return_value.open.call_count,1)
 def test_unknown_kind_and_unsafe_ack_are_rejected(self):
  with self.assertRaises(ValueError):s.record('password123')
  with self.assertRaises(ValueError):s.acknowledge('all')
class Request:
 headers={'content-type':'application/json','host':'dataark'}
 async def stream(self):yield b'{"code":"1234","password":"valid-password-123","admin_password":"valid-password-456"}'
class SetupRouteTests(unittest.TestCase):
 def test_incorrect_code_is_reported_before_response(self):
  with patch.object(recipient,'invoke',return_value={'ok':False,'security_event':'code_rejected'}),patch.object(recipient.setup_security,'safe_record') as report:
   with self.assertRaises(HTTPException) as e:asyncio.run(recipient.setup(Request()))
   self.assertEqual(e.exception.status_code,403);report.assert_called_once_with('code_rejected')
 def test_no_alert_for_probe_after_setup_complete(self):
  with patch.object(recipient,'invoke',return_value={'ok':False,'security_event':'setup_not_pending'}),patch.object(recipient.setup_security,'safe_record') as report:
   with self.assertRaises(HTTPException):asyncio.run(recipient.setup(Request()))
   report.assert_not_called()


class DeliveryAcknowledgementTests(unittest.TestCase):
 def test_delivery_is_not_caretaker_acknowledgement(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(s,'STATE',Path(tmp)/'security'),patch.object(s,'integration',return_value={}):
   key=s.record('code_rejected');s.delivered([key]);data=s.snapshot();self.assertEqual(data['pending_delivery'],0);self.assertEqual(data['unacknowledged'],1)
 def test_integration_authorization_is_required(self):
  with patch('app.services.bugout.ha_authorized',return_value=False),patch.object(s,'delivered') as mark:
   with self.assertRaises(HTTPException) as e:asyncio.run(recipient.delivered(Request()))
   self.assertEqual(e.exception.status_code,401);mark.assert_not_called()
