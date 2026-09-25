import unittest
from http.client import HTTPException
from unittest.mock import MagicMock, patch
from app.services import health
from app.models.services import Services


class KiwixTests(unittest.TestCase):
    def test_http_results(self):
        for status, body, expected in [
            (200, b"<title>Welcome to Kiwix Server</title>", "running"),
            (200, b"<title>Other service</title>", "unhealthy"),
            (503, b"Service unavailable", "unhealthy"),
            (302, b"", "unhealthy"),
        ]:
            with self.subTest(status=status, expected=expected):
                connection = MagicMock()
                connection.getresponse.return_value.status = status
                connection.getresponse.return_value.read.return_value = body
                with patch.object(health, "HTTPConnection", return_value=connection) as factory:
                    self.assertEqual(health.kiwix_state(), expected)
                factory.assert_called_once_with("127.0.0.1", 8080, timeout=2)
                connection.request.assert_called_once_with("GET", "/")
                connection.close.assert_called_once()

    def test_connection_failures(self):
        for error in [ConnectionRefusedError(), TimeoutError(), HTTPException()]:
            connection = MagicMock()
            connection.request.side_effect = error
            with patch.object(health, "HTTPConnection", return_value=connection):
                self.assertEqual(health.kiwix_state(), "unavailable")
            connection.close.assert_called_once()

    def test_kiwix_survives_systemctl_failure_and_serialization(self):
        with patch.object(health, "kiwix_state", return_value="unhealthy"), patch.object(health.subprocess, "run", side_effect=FileNotFoundError):
            states = Services.model_validate(health.services()).model_dump()
        self.assertEqual(states["kiwix"], "unhealthy")
        state, issues = health.assess(None, states, "Idle", [])
        self.assertEqual(state, "degraded")
        self.assertIn("kiwix: unhealthy", issues)

if __name__ == "__main__":
    unittest.main()
