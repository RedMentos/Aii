"""Run298 RED/GREEN: source-bound failed actions are observed negative outcomes.

Actual production Runtime/Store SQLite with synthetic action values; no model
weights, native inference, real-world causality, or acceptance-gate promotion.
"""
import json
from pathlib import Path
import tempfile
import time
import unittest

from v13.runtime import Runtime
from v13.store import Store
from v13 import world_model as W


class TerminalOutcomeBindingRun298(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.runtime = Runtime(self.home)
        self.runtime.sleep.cycle.set_policy("enabled", "off")
        self.actions = []
        self.sources = []
        self.statuses = []
        for i in range(24):
            event = self.runtime.store.event(
                self.runtime.session, f"World terminal outcome source {i}"
            )
            route = W.ACTIONS[i % len(W.ACTIONS)]
            with self.runtime.store.tx() as c:
                c.execute(
                    "INSERT INTO packets VALUES (?,?,?,?,?,?)",
                    (f"run298-route-{i}", "ActionSelection", event["event_id"],
                     event["brain_generation_id"], json.dumps({"route_hint": route}),
                     time.time() - 1.0),
                )
            action_id = self.runtime.store.start_action(
                event["event_id"], event["brain_generation_id"],
                forecast={
                    "input_chars": len(f"World terminal outcome source {i}"),
                    "resource_state": "NORMAL",
                    "profile": {"role": "C3_LANGUAGE"},
                },
            )
            status = "FINAL" if i < 16 else ("ERROR", "DEADLINE", "CANCELLED")[(i - 16) % 3]
            self.runtime.store.finish_action(
                action_id, status,
                {"action_duration_s": 0.5 + i * 0.07,
                 "characters": i + 1,
                 "role": "C3_LANGUAGE" if status == "FINAL" else None},
            )
            self.actions.append(action_id)
            self.sources.append(event["source_ref"]["source_id"])
            self.statuses.append(status)

    def tearDown(self):
        if self.runtime is not None:
            self.runtime.close()
        self.temp.cleanup()

    def test_failed_terminal_actions_fit_as_observed_zero_success(self):
        rows = W.transitions(self.runtime.store)
        self.assertEqual(len(rows), 24)
        self.assertEqual([x["y"][1] for x in rows].count(0.0), 8)
        self.assertEqual([x["y"][1] for x in rows].count(1.0), 16)
        state = W.fit(self.runtime.store, rng_seed=298)
        self.assertEqual(state["status"], "FITTED", state.get("status"))
        self.assertEqual(state["n"], 24)
        self.assertEqual(len(state["training_bindings"]), 24)
        self.assertEqual(state["evidence_scope"], "SOURCE_BOUND_STORE")
        self.assertIsNotNone(W.load(self.runtime.store))
        self.runtime.close()
        self.runtime = None
        fresh = Store(self.home)
        try:
            self.assertIsNotNone(W.load(fresh))
        finally:
            fresh.close()

    def test_nonfinal_status_and_outcome_tamper_invalidate_persisted_fit(self):
        self.assertEqual(W.fit(self.runtime.store)["status"], "FITTED")
        failed = self.actions[16]
        with self.runtime.store.tx() as c:
            c.execute("UPDATE actions SET status='FINAL' WHERE id=?", (failed,))
        self.assertIsNone(W.load(self.runtime.store))
        with self.runtime.store.tx() as c:
            c.execute("UPDATE actions SET status='ERROR' WHERE id=?", (failed,))
        self.assertIsNotNone(W.load(self.runtime.store))
        with self.runtime.store.tx() as c:
            c.execute("UPDATE actions SET outcome=? WHERE id=?", (
                json.dumps({"action_duration_s": 999.0,
                            "characters": 17, "role": None}), failed))
        self.assertIsNone(W.load(self.runtime.store))

    def test_nonfinal_source_revocation_invalidates_fitted_state(self):
        self.assertEqual(W.fit(self.runtime.store)["status"], "FITTED")
        with self.runtime.store.tx() as c:
            c.execute("UPDATE sources SET deleted=1 WHERE id=?", (self.sources[16],))
        self.assertIsNone(W.load(self.runtime.store))
        cf = W.counterfactual(self.runtime.store, W.state_vec(40), "simple")
        self.assertEqual(cf["label"], "SIMULATION_UNCERTAIN")
        self.assertIsNone(cf["prediction"])

    def test_dispatched_and_unknown_status_are_never_training_observations(self):
        for i, bad in enumerate(("DISPATCHED", "WAITING")):
            aid = self.actions[i]
            with self.runtime.store.tx() as c:
                c.execute("UPDATE actions SET status=? WHERE id=?", (bad, aid))
        rows = W.transitions(self.runtime.store)
        self.assertEqual(len(rows), 22)
        self.assertNotIn(self.actions[0], [x["action_id"] for x in rows])
        self.assertNotIn(self.actions[1], [x["action_id"] for x in rows])


if __name__ == "__main__":
    unittest.main()
