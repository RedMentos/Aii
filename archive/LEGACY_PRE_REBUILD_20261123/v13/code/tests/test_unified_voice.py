"""One external V13 answer per user turn, with native runners mocked.

This tests the release's runtime action gate, not native B1/B2/C3 inference
quality or a Redmi receipt. The protected Termux plain UI history patch is
separately exercised by the real pinned staging suite.
"""
from pathlib import Path
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from v13.operator import Operator
from v13.runtime import Runtime


class UnifiedRuntime(unittest.TestCase):
    def test_each_body_route_has_only_c3_external_voice(self):
        for route in ("simple", "detail", "gist", "both"):
            with self.subTest(route=route), tempfile.TemporaryDirectory() as temp:
                runtime = Runtime(Path(temp))
                try:
                    runtime.cfg["observer_mode"] = "off"  # isolate C5 egress only
                    runtime._route = Mock(return_value=(route, {"source": "TEST"}))
                    runtime.learner.output_delta = Mock(return_value=None)
                    roles = []
                    def get(role):
                        roles.append(role)
                        return SimpleNamespace(
                            role=role, last_metrics={"test_seam": True},
                            generate=lambda *a, **k: iter(["one shared answer"]))
                    runtime.pool.get = Mock(side_effect=get)
                    eid = Operator(runtime).run("A question about the plan")
                    stop_at = time.monotonic() + 8
                    while not runtime.idle() and time.monotonic() < stop_at:
                        time.sleep(.01)
                    self.assertTrue(runtime.idle())
                    rows = runtime.store.rows(
                        "SELECT * FROM messages WHERE event_id=? AND role='assistant'", (eid,))
                    self.assertEqual(len(rows), 1)
                    self.assertEqual(rows[0]["status"], "FINAL")
                    self.assertEqual(rows[0]["text"], "one shared answer")
                    self.assertTrue(roles)
                    self.assertEqual(set(roles), {"C3_LANGUAGE"})
                finally:
                    runtime.close()


if __name__ == "__main__":
    unittest.main()
