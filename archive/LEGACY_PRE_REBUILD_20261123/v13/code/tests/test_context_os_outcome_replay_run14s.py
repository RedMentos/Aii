"""Run14S preregistered test-first: one ContextOS event cannot mint many learning samples."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.runtime import Runtime
from v13 import context_os as C
from v13 import neuromod as N

LONG = "The garden and the weather were discussed with exact source references. " * 7


class ContextOutcomeReplay(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.c = C.ContextOS(self.r.store, self.r.cfg, None, N.Neuromod(self.r.store))

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def rated_event(self, name):
        e = self.r.store.event(self.r.session, name)["event_id"]
        history = []
        for i in range(12):
            history += [
                {"event_id": "older-%d" % i, "role": "user", "text": "Question %d. " % i + LONG},
                {"event_id": "older-%d" % i, "role": "assistant", "text": "Answer %d. " % i + LONG},
            ]
        p = self.c.plan(e, "C3_LANGUAGE", "SYS", [], history, name)
        self.assertIn("compress", " ".join(p["plan"]["decisions"]))
        return e

    def count(self):
        return self.c._load()[0].get("policy", {}).get("compress", {}).get("n", 0)

    def test_same_event_replay_cannot_fake_three_samples(self):
        e = self.rated_event("first")
        self.c.outcome(e, 0.0)
        self.assertEqual(self.count(), 1)
        self.c.outcome(e, 0.0)
        self.c.outcome(e, 0.0)
        self.assertEqual(self.count(), 1)
        self.assertEqual(self.c._shift(self.c._load()[0], "compress"), 0.0)

    def test_receipt_survives_context_controller_restart(self):
        e = self.rated_event("restart")
        self.c.outcome(e, 0.0)
        fresh = C.ContextOS(self.r.store, self.r.cfg, None, N.Neuromod(self.r.store))
        fresh.outcome(e, 0.0)
        self.assertEqual(fresh._load()[0]["policy"]["compress"]["n"], 1)

    def test_distinct_events_still_learn_and_activation_stays_human(self):
        for i in range(3):
            e = self.rated_event("distinct-%d" % i)
            self.c.outcome(e, 0.0)
        self.assertEqual(self.count(), 3)
        self.assertEqual(self.c._shift(self.c._load()[0], "compress"), 0.0)
        with self.assertRaises(PermissionError):
            self.c.set_mode("ACTIVE")
        self.c.set_mode("ACTIVE", "EXPLICIT_HUMAN", "learned")
        self.assertLess(self.c._shift(self.c._load()[0], "compress"), 0.0)

    def test_out_of_order_recent_and_evicted_old_event_replay(self):
        with patch.object(C, "OUTCOME_HISTORY_MAX", 4, create=True):
            events = [self.rated_event("window-%d" % i) for i in range(6)]
            self.c.outcome(events[1], 0.0)
            self.c.outcome(events[0], 0.0)  # recently older event still admissible
            self.assertEqual(self.count(), 2)
            for e in events[2:]:
                self.c.outcome(e, 0.0)
            self.assertEqual(self.count(), 6)
            self.c.outcome(events[0], 0.0)  # evicted from bounded receipt history
            self.assertEqual(self.count(), 6)


if __name__ == "__main__":
    unittest.main()
