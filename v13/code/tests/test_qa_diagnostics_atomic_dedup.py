"""Cross-instance diagnostic dedup and no-eviction QA regression."""
import tempfile
import threading
import unittest
from pathlib import Path

from v13.private_diagnostics_bridge import DiagnosticBridge


class DiagnosticAtomicDedupTests(unittest.TestCase):
    def test_two_preloaded_instances_execute_only_once(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "seen.json"
            calls = []
            barrier = threading.Barrier(2)
            def metrics():
                calls.append(1)
                return {"ready": True}
            instances = [
                DiagnosticBridge(path, allowed_authors={"operator"}, metrics={"HEALTH": metrics}, enabled=True)
                for _ in range(2)
            ]
            request = {"id": "request-000001", "command": "HEALTH", "expires_at": 200, "author": "operator"}
            results = []
            def run(instance):
                barrier.wait()
                results.append(instance.handle(request, private_relay=True, authenticated_author="operator", now=100)["status"])
            threads = [threading.Thread(target=run, args=(instance,)) for instance in instances]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=5)
                self.assertFalse(thread.is_alive(), "diagnostic lock deadlocked")
            self.assertCountEqual(results, ["OK", "DUPLICATE"])
            self.assertEqual(len(calls), 1)
            reopened = DiagnosticBridge(path, allowed_authors={"operator"}, metrics={"HEALTH": metrics}, enabled=True)
            self.assertEqual(reopened.handle(request, private_relay=True, authenticated_author="operator", now=100)["status"], "DUPLICATE")

    def test_capacity_fails_closed_without_forgetting_valid_id(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "seen.json"
            calls = []
            bridge = DiagnosticBridge(path, allowed_authors={"operator"}, metrics={"HEALTH": lambda: calls.append(1) or {"ready": True}}, enabled=True, max_seen=1)
            def request(n):
                return {"id": f"request-{n:06d}", "command": "HEALTH", "expires_at": 200, "author": "operator"}
            def handle(n):
                return bridge.handle(request(n), private_relay=True, authenticated_author="operator", now=100)["status"]
            self.assertEqual(handle(1), "OK")
            self.assertEqual(handle(2), "CAPACITY")
            self.assertEqual(handle(1), "DUPLICATE")
            self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
