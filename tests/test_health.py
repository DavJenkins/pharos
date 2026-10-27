import subprocess
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

from app.models.status import StatusResponse
from app.services import health, status_service, resources

RESOURCES = {"cpu": {"temperature_c": 40.0, "load": [0.0, 0.0, 0.0]},
             "memory": {"used": "1 GiB", "available": "1 GiB", "swap_used": "0 B"},
             "storage": {"sd": {"used": "1 GiB", "free": "2 GiB", "percent": 20},
                         "ssd": {"used": "1 GiB", "free": "2 GiB", "percent": 20}}}
SERVICES = {"fastapi": "running", "apache": "running", "network_manager": "running", "samba": "running"}

class HealthTests(unittest.TestCase):
    @patch("app.services.update_status.progress", return_value=None)
    def test_sync_exit_codes_and_timeout(self, _progress):
        for code, state in [(0, "Syncing"), (1, "Idle"), (2, "Unavailable")]:
            with self.subTest(code=code), patch.object(health.subprocess, "run", return_value=SimpleNamespace(returncode=code)):
                self.assertEqual(health.sync_state(), state)
        with patch.object(health.subprocess, "run", side_effect=subprocess.TimeoutExpired("pgrep", 2)):
            self.assertEqual(health.sync_state(), "Unavailable")

    def test_worker_status_takes_precedence_over_rsync(self):
        for label in ("Waiting to update", "Downloading: Wikipedia (30%)", "Idle", "Update status unavailable"):
            with self.subTest(label=label), patch("app.services.update_status.progress", return_value={"label": label}), patch.object(health.subprocess, "run") as run:
                self.assertEqual(health.sync_state(), label)
                run.assert_not_called()

    def test_thresholds(self):
        for temp, disk, expected in [(40, 20, "ok"), (70, 20, "degraded"), (80, 20, "error"), (40, 80, "degraded"), (40, 90, "error"), (None, 20, "degraded"), (40, None, "degraded")]:
            data = deepcopy(RESOURCES)
            data["cpu"]["temperature_c"] = temp
            data["storage"]["ssd"]["percent"] = disk
            with self.subTest(temp=temp, disk=disk):
                self.assertEqual(health.assess(data, SERVICES, "Idle", [])[0], expected)

    @patch.object(health, "kiwix_state", return_value="running")
    def test_service_states(self, _kiwix):
        output = "Id=apache2.service\nLoadState=loaded\nActiveState=active\n\nId=smbd.service\nLoadState=loaded\nActiveState=failed\n\nId=NetworkManager.service\nLoadState=not-found\nActiveState=inactive\n"
        with patch.object(health.subprocess, "run", return_value=SimpleNamespace(stdout=output)):
            states = health.services()
        self.assertEqual(states["apache"], "running")
        self.assertEqual(states["samba"], "failed")
        self.assertEqual(states["network_manager"], "not_installed")
        state, issues = health.assess(RESOURCES, states, "Idle", [])
        self.assertEqual(state, "degraded")
        self.assertIn("samba: failed", issues)

    @patch.object(health, "kiwix_state", return_value="running")
    def test_service_probe_failure(self, _kiwix):
        with patch.object(health.subprocess, "run", side_effect=FileNotFoundError):
            self.assertEqual(health.services()["apache"], "unknown")

    @patch.object(status_service, "progress", return_value=None)
    @patch.object(status_service.Path, "exists", return_value=False)
    def test_partial_collection_serializes(self, _exists, _progress):
        with patch.object(status_service, "network", side_effect=OSError), patch.object(status_service, "system", return_value={"hostname": "test", "platform": "Pi", "uptime": "1 hour"}), patch.object(status_service, "resources", return_value=RESOURCES), patch.object(status_service, "services", return_value=SERVICES), patch.object(status_service, "sync_state", return_value="Idle"):
            data = StatusResponse.model_validate(status_service.get_status()).model_dump()
        self.assertIsNone(data["network"])
        self.assertEqual(data["status"]["state"], "degraded")
        self.assertEqual(data["resources"], RESOURCES)
        self.assertTrue(data["status"]["updated"].endswith("+00:00"))

    def test_resource_unknowns(self):
        with patch.object(resources, "_run", return_value=""), patch.object(resources.Path, "read_text", side_effect=OSError):
            self.assertIsNone(resources._cpu_temp())
            self.assertIsNone(resources._df("/")["percent"])
        with patch.object(resources.Path, "is_mount", return_value=False), patch.object(resources, "_run") as run:
            self.assertIsNone(resources._df("/mnt/storage")["percent"])
            run.assert_not_called()

if __name__ == "__main__":
    unittest.main()

class ThermalProbeTests(unittest.TestCase):
    def test_temperature_uses_kernel_sensor_without_firmware_process(self):
        with patch.object(resources.Path,'read_text',return_value='53125'),patch.object(resources,'_run') as command:
            self.assertEqual(resources._cpu_temp(),53.125)
            command.assert_not_called()
    def test_invalid_and_missing_thermal_sensor_are_unknown(self):
        for value in ['not a temperature','9999999']:
            with patch.object(resources.Path,'read_text',return_value=value):self.assertIsNone(resources._cpu_temp())
        with patch.object(resources.Path,'read_text',side_effect=OSError):self.assertIsNone(resources._cpu_temp())
