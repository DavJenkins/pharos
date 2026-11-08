import asyncio,json,unittest
from types import SimpleNamespace
from unittest.mock import patch
from fastapi import HTTPException
from app.routers import power
from tools import network_helper as helper
class Request:
 def __init__(self,data):self.headers={'authorization':'Basic test','content-type':'application/json'};self.body=json.dumps(data).encode()
 async def stream(self):yield self.body
class PowerTests(unittest.TestCase):
 def test_unauthorized_never_schedules(self):
  with patch.object(power,'authorized',return_value=False),patch.object(power,'invoke') as invoke:
   with self.assertRaises(HTTPException) as e:asyncio.run(power.control(Request({'operation':'shutdown','confirmed':True})))
   self.assertEqual(e.exception.status_code,401);invoke.assert_not_called()
 def test_confirmation_and_fixed_operation_required(self):
  for data in [{},{'operation':'restart','confirmed':False},{'operation':'shutdown','confirmed':1},{'operation':'reboot; touch /tmp/x','confirmed':True},{'operation':'shutdown','confirmed':True,'command':'anything'}]:
   with self.subTest(data=data),patch.object(power,'authorized',return_value=True),patch.object(power,'invoke') as invoke:
    with self.assertRaises(HTTPException):asyncio.run(power.control(Request(data)))
    invoke.assert_not_called()
 def test_container_cannot_control_host(self):
  with patch.object(power,'authorized',return_value=True),patch.object(power,'available',return_value=False),patch.object(power,'invoke') as invoke:
   with self.assertRaises(HTTPException) as e:asyncio.run(power.control(Request({'operation':'shutdown','confirmed':True})))
   self.assertEqual(e.exception.status_code,409);invoke.assert_not_called()
 def test_authenticated_dispatch(self):
  for operation in ('restart','shutdown'):
   with self.subTest(operation=operation),patch.object(power,'authorized',return_value=True),patch.object(power,'available',return_value=True),patch.object(power,'invoke',return_value={'ok':True}) as invoke:
    self.assertTrue(asyncio.run(power.control(Request({'operation':operation,'confirmed':True})))['ok']);invoke.assert_called_once_with({'action':'power','operation':operation,'confirmed':True})
 def test_helper_fixed_delayed_commands(self):
  for operation,command in [('restart','reboot'),('shutdown','poweroff')]:
   with self.subTest(operation=operation),patch.object(helper.Path,'is_dir',return_value=True),patch.object(helper.Path,'exists',return_value=False),patch.object(helper.subprocess,'run',return_value=SimpleNamespace(returncode=0)) as run:
    self.assertTrue(helper.execute({'action':'power','operation':operation,'confirmed':True})['ok']);self.assertEqual(run.call_args.args[0],['/usr/bin/systemd-run','--unit=dataark-caretaker-power','--on-active=5s','/usr/bin/systemctl',command])
 def test_helper_rejects_unconfirmed_and_extra_arguments(self):
  for data in [{'action':'power','operation':'shutdown'},{'action':'power','operation':'restart','confirmed':True,'command':'bad'}]:
   with patch.object(helper.subprocess,'run') as run:
    with self.assertRaises(ValueError):helper.execute(data)
    run.assert_not_called()
 def test_helper_refuses_container_and_scheduler_failure(self):
  with patch.object(helper.Path,'is_dir',return_value=False),patch.object(helper.subprocess,'run') as run:
   with self.assertRaises(helper.NetworkError):helper.execute({'action':'power','operation':'shutdown','confirmed':True})
   run.assert_not_called()
  with patch.object(helper.Path,'is_dir',return_value=True),patch.object(helper.Path,'exists',return_value=False),patch.object(helper.subprocess,'run',return_value=SimpleNamespace(returncode=1)):
   with self.assertRaises(helper.NetworkError):helper.execute({'action':'power','operation':'restart','confirmed':True})
