"""A gate-state write failure must not leave an orphaned human-approval request.

Real SQLite Store transaction and injected trigger; synthetic trainer only.
"""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.agi.weights import WeightConsolidation


class SyntheticTrainer:
    method = "synthetic-gate-atomic"

    def __init__(self):
        self.cfg = {"anchor_weight": .2, "targets": ("w1",)}

    def fit(self, items, base_generation, cancel=None, deadline=None):
        return {"artifact": "synthetic-candidate", "hash": "b" * 64,
                "method": self.method, "metrics": {"kl_to_base": .01}}


class GateRequestAtomic(unittest.TestCase):
    def test_failed_state_write_rolls_back_request_then_retry_creates_exactly_one(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            runtime = Runtime(home)
            runtime.sleep.cycle.set_policy("enabled", "off")
            bid = None
            try:
                event = runtime.store.event(runtime.session, "Source-backed budget?")
                runtime.memory.feedback(event["event_id"], "fact", "120 EUR")
                wc = WeightConsolidation(
                    runtime.store,
                    runtime.cfg | {"learning_mode": "SHADOW_UPDATE"},
                    trainer=SyntheticTrainer())
                bid = wc.stage(require_replay_pass=False)["batch_id"]
                self.assertEqual(wc.train(bid)["status"], "TRAINED")
                base = {"overall": .8, "unseen": .75}
                candidate = {"overall": .8, "unseen": .75,
                             "forgetting": {"rate": 0.}}
                with runtime.store.tx() as conn:
                    conn.execute("""
                        CREATE TRIGGER ag6_gate_write_fail BEFORE INSERT ON states
                        WHEN NEW.key='G6_WEIGHT_CONSOLIDATION'
                        BEGIN SELECT RAISE(ABORT, 'injected gate state failure'); END
                    """)
                with self.assertRaises(sqlite3.DatabaseError):
                    wc.gate(bid, base, candidate, learned_recall=1.)
                # The old code committed a request *before* the state write,
                # so this counterexample detects a durable orphan.
                self.assertEqual(runtime.store.one(
                    "SELECT COUNT(*) AS n FROM requests "
                    "WHERE kind='WEIGHT_CONSOLIDATION'")["n"], 0)
                self.assertEqual(wc.batch(bid)["status"], "TRAINED")
                with runtime.store.tx() as conn:
                    conn.execute("DROP TRIGGER ag6_gate_write_fail")
                result = wc.gate(bid, base, candidate, learned_recall=1.)
                self.assertEqual(result["status"], "PENDING_USER")
                self.assertIsNotNone(result["request_id"])
                self.assertEqual(runtime.store.one(
                    "SELECT COUNT(*) AS n FROM requests "
                    "WHERE kind='WEIGHT_CONSOLIDATION'")["n"], 1)
                self.assertEqual(runtime.store.one(
                    "SELECT id FROM requests WHERE kind='WEIGHT_CONSOLIDATION'")["id"],
                    result["request_id"])
            finally:
                runtime.close()
            restarted = Runtime(home)
            try:
                batch = WeightConsolidation(
                    restarted.store, restarted.cfg,
                    trainer=SyntheticTrainer()).batch(bid)
                self.assertEqual(batch["status"], "PENDING_USER")
                self.assertEqual(restarted.store.one(
                    "SELECT COUNT(*) AS n FROM requests "
                    "WHERE kind='WEIGHT_CONSOLIDATION'")["n"], 1)
            finally:
                restarted.close()


if __name__ == "__main__":
    unittest.main()
