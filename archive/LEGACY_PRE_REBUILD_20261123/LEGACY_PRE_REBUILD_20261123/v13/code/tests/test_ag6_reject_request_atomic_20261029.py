"""AG6 reject must update the batch and its approval request atomically.

Real SQLite Store + injected failure; synthetic trainer, no native weights or authority.
"""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.agi.weights import WeightConsolidation


class SyntheticTrainer:
    method = "synthetic-ag6-reject-atomic"

    def __init__(self):
        self.cfg = {"anchor_weight": .2, "targets": ("w1",)}

    def fit(self, items, base_generation, cancel=None, deadline=None):
        return {"artifact": "synthetic-candidate", "hash": "c" * 64,
                "method": self.method, "metrics": {"kl_to_base": .01}}


class RejectRequestAtomic(unittest.TestCase):
    def _ready(self, runtime):
        event = runtime.store.event(runtime.session, "Source-backed budget?")
        runtime.memory.feedback(event["event_id"], "fact", "120 EUR")
        wc = WeightConsolidation(
            runtime.store, runtime.cfg | {"learning_mode": "SHADOW_UPDATE"},
            trainer=SyntheticTrainer())
        bid = wc.stage(require_replay_pass=False)["batch_id"]
        self.assertEqual(wc.train(bid)["status"], "TRAINED")
        return wc, bid

    def _pending(self, runtime):
        wc, bid = self._ready(runtime)
        out = wc.gate(
            bid, {"overall": .8, "unseen": .75},
            {"overall": .8, "unseen": .75, "forgetting": {"rate": 0.}},
            learned_recall=1.)
        self.assertEqual(out["status"], "PENDING_USER")
        self.assertEqual(runtime.store.one(
            "SELECT status FROM requests WHERE id=?", (out["request_id"],))["status"], "PENDING")
        return wc, bid, out["request_id"]

    def test_failed_batch_state_write_cannot_cancel_pending_request(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            runtime = Runtime(home)
            runtime.sleep.cycle.set_policy("enabled", "off")
            try:
                wc, bid, rid = self._pending(runtime)
                with runtime.store.tx() as conn:
                    conn.execute("""
                        CREATE TRIGGER ag6_reject_state_abort BEFORE INSERT ON states
                        WHEN NEW.key='G6_WEIGHT_CONSOLIDATION'
                        BEGIN SELECT RAISE(ABORT, 'injected rejection state failure'); END
                    """)
                with self.assertRaises(sqlite3.DatabaseError):
                    wc.reject(bid, "explicit user rejection")
                self.assertEqual(wc.batch(bid)["status"], "PENDING_USER")
                self.assertEqual(runtime.store.one(
                    "SELECT status FROM requests WHERE id=?", (rid,))["status"], "PENDING")
                with runtime.store.tx() as conn:
                    conn.execute("DROP TRIGGER ag6_reject_state_abort")
                self.assertEqual(wc.reject(bid, "explicit user rejection")["status"], "REJECTED")
                self.assertEqual(runtime.store.one(
                    "SELECT status FROM requests WHERE id=?", (rid,))["status"], "REJECTED")
            finally:
                runtime.close()
            restarted = Runtime(home)
            try:
                self.assertEqual(WeightConsolidation(
                    restarted.store, restarted.cfg,
                    trainer=SyntheticTrainer()).batch(bid)["status"], "REJECTED")
                self.assertEqual(restarted.store.one(
                    "SELECT status FROM requests WHERE id=?", (rid,))["status"], "REJECTED")
            finally:
                restarted.close()

    def test_missing_pending_request_cannot_commit_rejection(self):
        with tempfile.TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            runtime.sleep.cycle.set_policy("enabled", "off")
            try:
                wc, bid, rid = self._pending(runtime)
                with runtime.store.tx() as conn:
                    conn.execute("UPDATE requests SET status='REJECTED' WHERE id=?", (rid,))
                with self.assertRaises(ValueError):
                    wc.reject(bid, "stale request")
                self.assertEqual(wc.batch(bid)["status"], "PENDING_USER")
                self.assertEqual(runtime.store.one(
                    "SELECT status FROM requests WHERE id=?", (rid,))["status"], "REJECTED")
            finally:
                runtime.close()

    def test_unrequested_and_repeated_rejection_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            runtime.sleep.cycle.set_policy("enabled", "off")
            try:
                wc, bid = self._ready(runtime)
                self.assertEqual(wc.reject(bid)["status"], "REJECTED")
                self.assertEqual(wc.reject(bid)["status"], "REJECTED")
                self.assertIsNone(wc.batch(bid)["request_id"])
            finally:
                runtime.close()


if __name__ == "__main__":
    unittest.main()
