"""Run371 RED-first: teacher results cannot outlive cancellation or request ownership."""
from pathlib import Path
import tempfile
import threading
import unittest

from v13.runtime import Runtime
from v13.agi import hub


class TeacherFulfilCancelRun371(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = Runtime(Path(self.tmp.name))
        self.runtime.sleep.cycle.set_policy("enabled", "off")
        self.teacher = hub(self.runtime).teacher

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def _state(self):
        return self.teacher.box.load()[0]

    def test_cancel_set_during_backend_does_not_publish_trace(self):
        cancel = threading.Event()
        calls = []
        def backend(prompt):
            calls.append(prompt)
            cancel.set()
            return {"answer": "late unapproved output"}
        self.teacher.register("slow_local", backend)
        rid = self.teacher.request("Ordinary safe question")
        self.assertIsNone(self.teacher.fulfil(rid, "slow_local", cancel=cancel))
        self.assertEqual(len(calls), 1)
        self.assertEqual(self._state()["requests"][rid]["status"], "OPEN")
        self.assertEqual(self._state()["traces"], [])

    def test_already_cancelled_never_calls_backend(self):
        cancel = threading.Event()
        cancel.set()
        self.teacher.register("local", lambda prompt: self.fail("backend was called"))
        rid = self.teacher.request("Ordinary safe question")
        self.assertIsNone(self.teacher.fulfil(rid, "local", cancel=cancel))
        self.assertEqual(self._state()["requests"][rid]["status"], "OPEN")

    def test_stale_backend_cannot_overwrite_terminal_request(self):
        rid = self.teacher.request("Ordinary safe question")
        def backend(prompt):
            def terminal(st):
                st["requests"][rid]["status"] = "DENIED_CLOUD"
            self.teacher.box.mutate(terminal)
            return {"answer": "stale result"}
        self.teacher.register("local", backend)
        self.assertIsNone(self.teacher.fulfil(rid, "local"))
        self.assertEqual(self._state()["requests"][rid]["status"], "DENIED_CLOUD")
        self.assertEqual(self._state()["traces"], [])

    def test_cloud_revoke_during_backend_prevents_reference_commit(self):
        self.teacher.allow_cloud(True)
        rid = self.teacher.request("Ordinary safe question")
        def backend(prompt):
            self.teacher.allow_cloud(False)
            return {"answer": "cloud result after revocation"}
        self.teacher.register("cloud_test", backend, kind="cloud")
        self.assertIsNone(self.teacher.fulfil(rid, "cloud_test"))
        self.assertFalse(self._state()["cloud_allowed"])
        self.assertEqual(self._state()["requests"][rid]["status"], "DENIED_CLOUD")
        self.assertEqual(self._state()["traces"], [])

    def test_normal_local_reference_persists_with_no_truth_promotion(self):
        self.teacher.register("local", lambda prompt: {"answer": "Reference answer", "model": "local-fake"})
        rid = self.teacher.request("Ordinary safe question")
        trace = self.teacher.fulfil(rid, "local")
        self.assertEqual(trace["authority"], "REFERENCE_NOT_FACT")
        self.assertEqual(self._state()["requests"][rid]["status"], "DONE")
        self.assertEqual(len(self._state()["traces"]), 1)
        self.assertEqual(self.teacher.dataset()[0]["target"], "Reference answer")


if __name__ == "__main__":
    unittest.main()
