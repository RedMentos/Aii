"""Run117CA: backlog catch-up reaches live ContextOS/C3 and obeys source revocation.

Actual Runtime/Store and synthetic C3 seam only; no native model or learning.
"""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import tempfile
import time
import unittest

from v13.runtime import Runtime
from v13 import sleep_offline as S


class BacklogContextConsumer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.r.sleep.cycle.set_policy("tick_seconds", "300")
        self.r.cfg["history_turns"] = 0
        self.captured = []
        self.r._route = Mock(return_value=("simple", {"source": "TEST_ROUTE_SEAM"}))
        self.r.learner.output_delta = Mock(return_value=None)

        def generate(messages, *args, **kwargs):
            self.captured.append(messages)
            yield "synthetic C3 output"

        self.r.pool.get = Mock(return_value=SimpleNamespace(
            role="C3_LANGUAGE", last_metrics={}, generate=generate))

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def stored_turn(self, i):
        text = f"RUN117CA_EXACT_MARKER_{i:03d}"
        e = self.r.store.event(self.r.session, text)
        self.r.store.message(self.r.session, e["event_id"], "assistant",
                             f"Noted synthetic marker {i:03d}.",
                             "FINAL", {"direct_source_copy": True})
        return e

    def submit(self, text):
        self.r.submit(text)
        deadline = time.monotonic() + 15
        while not self.r.idle() and time.monotonic() < deadline:
            time.sleep(.005)
        self.assertTrue(self.r.idle())
        self.assertEqual(self.r.last_answer()["status"], "FINAL")
        return str(self.captured[-1])

    def test_seventy_turns_reach_live_c3_only_after_catchup_and_revoke(self):
        refs = [self.stored_turn(i) for i in range(70)]
        first = S.digest(self.r.store)
        self.assertEqual((first["turns"], first["backlog_sessions"]), (64, 1))
        old = "\n".join(S.context_items(self.r.store, self.r.session, cap=20000))
        self.assertIn("RUN117CA_EXACT_MARKER_063", old)
        self.assertNotIn("RUN117CA_EXACT_MARKER_069", old)
        second = S.digest(self.r.store)
        self.assertEqual((second["turns"], second["backlog_sessions"]), (6, 0))
        latest = "\n".join(S.context_items(self.r.store, self.r.session, cap=20000))
        self.assertIn("RUN117CA_EXACT_MARKER_069", latest)
        self.assertIn("RUN117CA_EXACT_MARKER_000", latest)
        live = self.submit("What is the latest previously stored marker?")
        self.assertIn("RUN117CA_EXACT_MARKER_069", live)
        with self.r.store.tx() as c:
            c.execute("UPDATE sources SET deleted=1 WHERE id=?",
                      (refs[-1]["source_ref"]["source_id"],))
        revoked = self.submit("Check whether the latest stored marker is still available.")
        self.assertNotIn("RUN117CA_EXACT_MARKER_069", revoked)
        self.assertNotIn("RUN117CA_EXACT_MARKER_069",
                         "\n".join(S.context_items(self.r.store, self.r.session, cap=20000)))


if __name__ == "__main__":
    unittest.main()
