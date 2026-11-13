"""Offline QA regression: explicit Android AI start must not fabricate success."""
import unittest
from unittest import mock

from v13 import chat_service as ai


class ExplicitStartTruthTests(unittest.TestCase):
    def _service(self, result=None, failure=None):
        console = mock.Mock()
        if failure is not None:
            console.start.side_effect = failure
        else:
            console.start.return_value = result
        service = ai.ChatService(console)
        return service, console

    def _run(self, service):
        with mock.patch.object(ai, "_desired"), \
             mock.patch.object(ai.lifecycle, "STOP_REQUEST") as stop, \
             mock.patch("v13.pipeline_agent.snapshot",
                        return_value={"last_result": "UP_TO_DATE"}):
            stop.exists.return_value = False
            return service.command("start", {})

    def test_native_start_exception_is_not_reported_as_started(self):
        service, console = self._service(failure=RuntimeError("native launch failed"))
        self.assertEqual(self._run(service), {"status": "LAUNCH_FAILED"})
        self.assertEqual(service.status, "LAUNCH_FAILED")
        self.assertGreater(service.next_retry, 0)
        console.start.assert_called_once()

    def test_native_refusal_is_not_reported_as_started(self):
        service, _ = self._service(result={"status": "TIME_BUDGET"})
        self.assertEqual(self._run(service), {"status": "LAUNCH_FAILED"})
        self.assertEqual(service.status, "LAUNCH_FAILED")

    def test_native_already_running_is_truthful(self):
        service, _ = self._service(result={"status": "ALREADY_RUNNING"})
        self.assertEqual(self._run(service), {"status": "ALREADY_RUNNING"})
        self.assertEqual(service.status, "RUNNING")

    def test_native_started_is_truthful(self):
        service, _ = self._service(result={"status": "STARTED"})
        self.assertEqual(self._run(service), {"status": "STARTED"})
        self.assertEqual(service.status, "RUNNING")


if __name__ == "__main__":
    unittest.main()
