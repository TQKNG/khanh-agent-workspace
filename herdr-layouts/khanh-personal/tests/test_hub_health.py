"""The local hub health report is safe to expose to its authenticated UI client."""

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hub"))

import cockpit_hub  # noqa: E402


class HealthReport(unittest.TestCase):
    def setUp(self):
        cockpit_hub._HEALTH_VALUE = None
        cockpit_hub._HEALTH_AT = 0.0

    def test_reports_missing_github_and_git_without_leaking_command_output(self):
        with mock.patch.object(cockpit_hub.shutil, "which", return_value=None):
            report = cockpit_hub.health_report()
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["capabilities"]["github"]["status"], "missing_cli")
        self.assertEqual(report["capabilities"]["git"]["status"], "missing_cli")
        self.assertNotIn("token", str(report).lower())

    def test_reports_gh_authentication_as_a_state_not_raw_output(self):
        completed = mock.Mock(returncode=0, stdout="Logged in as private-user", stderr="")
        with (
            mock.patch.object(cockpit_hub.shutil, "which", side_effect=lambda name: f"/{name}" if name in {"gh", "git"} else None),
            mock.patch.object(cockpit_hub.subprocess, "run", return_value=completed),
        ):
            report = cockpit_hub.health_report()
        self.assertEqual(report["capabilities"]["github"]["status"], "ready")
        self.assertNotIn("private-user", str(report))

    def test_reports_missing_auth_without_echoing_gh_diagnostics(self):
        completed = mock.Mock(returncode=1, stdout="secret-account", stderr="private token detail")
        with (
            mock.patch.object(cockpit_hub.shutil, "which", side_effect=lambda name: f"/{name}" if name in {"gh", "git"} else None),
            mock.patch.object(cockpit_hub.subprocess, "run", return_value=completed),
        ):
            report = cockpit_hub.health_report()
        self.assertEqual(report["capabilities"]["github"]["status"], "login_required")
        self.assertNotIn("private", str(report))


if __name__ == "__main__":
    unittest.main()
