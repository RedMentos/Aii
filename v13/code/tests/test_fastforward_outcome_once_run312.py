"""Run312 RED/GREEN: exact-once FastForward outcome learning on real Runtime/Store SQLite.

Synthetic timings only; no native models, no learning authority promotion.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import unittest

from v13.runtime import Runtime
from v13.fastforward import FastForward, features, KEY
from v13 import fastforward as F


class FastForwardOutcomeOnceRun312(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.f = FastForward(self.r.store)
        self.x = features("what is 40 plus 2", "simple", "none")

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def event(self, label):
        return self.r.store.event(self.r.session, label)["event_id"]

    def test_same_event_replay_does_not_double_learn_or_change_version(self):
        eid = self.event("run312 first")
        first = self.f.learn(eid, self.x, 2.0, "FINAL", 20)
        state, version = self.f._load()
        again = self.f.learn(eid, self.x, 2.0, "FINAL", 20)
        self.assertEqual(first, again)
        self.assertEqual(self.f._load(), (state, version))
        self.assertEqual(self.f.report()["trained_on"], 1)
        self.assertEqual(len(self.f._load()[0]["replay"]), 1)

    def test_conflicting_replay_fails_closed_without_mutating_weights(self):
        eid = self.event("run312 conflict")
        self.f.learn(eid, self.x, 2.0, "FINAL", 20)
        original = self.f._load()
        with self.assertRaises(ValueError):
            self.f.learn(eid, self.x, 5.0, "FINAL", 20)
        self.assertEqual(self.f._load(), original)

    def test_first_receipt_survives_bounded_replay_and_restart(self):
        eid = self.event("run312 original")
        original = self.f.learn(eid, self.x, 2.0, "FINAL", 20)
        for i in range(270):
            self.f.learn(self.event(f"run312 other {i}"), self.x, 1.0 + i * .01, "FINAL", 21)
        self.assertEqual(self.f.report()["trained_on"], 271)
        self.r.close()
        self.r = Runtime(self.home)
        self.f = FastForward(self.r.store)
        state, version = self.f._load()
        self.assertEqual(self.f.learn(eid, self.x, 2.0, "FINAL", 20), original)
        self.assertEqual(self.f._load(), (state, version))
        self.assertEqual(self.f.report()["trained_on"], 271)

    def test_concurrent_duplicate_calls_are_one_transaction(self):
        eid = self.event("run312 concurrency")
        f2 = FastForward(self.r.store)
        with ThreadPoolExecutor(max_workers=2) as pool:
            a, b = list(pool.map(lambda f: f.learn(eid, self.x, 2.0, "FINAL", 20), (self.f, f2)))
        self.assertEqual(a, b)
        self.assertEqual(self.f.report()["trained_on"], 1)
        self.assertEqual(len(self.f._load()[0]["replay"]), 1)

    def test_neuromod_receipt_not_reemitted_after_warmup(self):
        n = Mock()
        n.step_scale.return_value = 1.0
        f = FastForward(self.r.store, n)
        for i in range(3):
            f.learn(self.event(f"run312 warmup {i}"), self.x, 2.0, "FINAL", 20)
        n.touch.reset_mock()
        n.signal.reset_mock()
        eid = self.event("run312 N10")
        result = f.learn(eid, self.x, 3.0, "FINAL", 20)
        state, version = f._load()
        self.assertEqual(f.learn(eid, self.x, 3.0, "FINAL", 20), result)
        self.assertEqual(f._load(), (state, version))
        self.assertEqual(n.touch.call_count, 1)
        self.assertEqual(n.signal.call_count, 1)

    def test_receipt_serialization_failure_rolls_back_predictor_atomically(self):
        eid = self.event("run312 atomic crash window")
        before = self.f._load()
        real_dumps = F.dumps
        def fail_receipt(value):
            if isinstance(value, dict) and "fingerprint" in value:
                raise RuntimeError("injected receipt serialization failure")
            return real_dumps(value)
        with patch.object(F, "dumps", side_effect=fail_receipt):
            with self.assertRaisesRegex(RuntimeError, "injected receipt"):
                self.f.learn(eid, self.x, 2.0, "FINAL", 20)
        self.assertEqual(self.f._load(), before)
        self.assertEqual(self.r.store.one(
            "SELECT COUNT(*) AS n FROM states WHERE key LIKE 'F_FAST_FORWARD_RECEIPT_%'")["n"], 0)
        self.assertEqual(self.r.store.integrity(True), [])
        self.f.learn(eid, self.x, 2.0, "FINAL", 20)
        self.assertEqual(self.f.report()["trained_on"], 1)

    def test_distinct_events_still_update_predictor(self):
        first = self.event("run312 distinct A")
        second = self.event("run312 distinct B")
        self.f.learn(first, self.x, 2.0, "FINAL", 20)
        st1, v1 = self.f._load()
        self.f.learn(second, self.x, 3.0, "FINAL", 21)
        st2, v2 = self.f._load()
        self.assertEqual(st2["n"], 2)
        self.assertEqual(v2, v1 + 1)
        self.assertNotEqual(st1["w"], st2["w"])


if __name__ == "__main__":
    unittest.main()
