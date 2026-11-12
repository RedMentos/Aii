"""Regression: local user OFF survives an update resume request."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from v13 import chat_service, lifecycle, pipeline_agent


class Console:
    def __init__(self):
        self.running = False
        self.starts = 0

    def state(self):
        return {"running": self.running}

    def start(self):
        self.starts += 1
        self.running = True
        return {"status": "STARTED"}


class OffDuringUpdateTests(unittest.TestCase):
    def test_resume_marker_consumed_without_launch_when_off(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "resume.json"
            with mock.patch.object(lifecycle, "RESUME", marker), mock.patch.object(lifecycle, "PRIVATE", Path(directory)):
                lifecycle.request_resume(reason="UPDATED")
                console = Console()
                self.assertFalse(lifecycle.service_resume(console, allowed=False))
                self.assertEqual(console.starts, 0)
                self.assertFalse(marker.exists())
                self.assertFalse(lifecycle.service_resume(console, allowed=True))

    def test_explicit_on_still_resumes(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "resume.json"
            with mock.patch.object(lifecycle, "RESUME", marker), mock.patch.object(lifecycle, "PRIVATE", Path(directory)):
                lifecycle.request_resume(reason="UPDATED")
                console = Console()
                self.assertTrue(lifecycle.service_resume(console, allowed=True))
                self.assertEqual(console.starts, 1)
                self.assertFalse(marker.exists())

    def test_daemon_tick_does_not_restart_off_service(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "resume.json"
            with mock.patch.object(lifecycle, "RESUME", marker), mock.patch.object(lifecycle, "PRIVATE", Path(directory)), \
                 mock.patch.object(chat_service, "_read_desired", return_value=False), \
                 mock.patch.object(lifecycle, "service_stop", return_value=False), \
                 mock.patch.object(lifecycle, "STOP_REQUEST", Path(directory) / "no-stop"), \
                 mock.patch.object(pipeline_agent, "snapshot", return_value={"last_result": "UP_TO_DATE"}), \
                 mock.patch.object(pipeline_agent, "refresh_requested", return_value=False):
                lifecycle.request_resume(reason="UPDATED")
                console = Console()
                daemon = chat_service.ChatService(console=console)
                daemon.tick()
                self.assertEqual(daemon.status, "STOPPED_BY_USER")
                self.assertEqual(console.starts, 0)
                self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
