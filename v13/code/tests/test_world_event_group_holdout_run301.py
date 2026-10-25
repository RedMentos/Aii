"""Run301 RED/GREEN: WorldModel heldout must be disjoint by source user event.

Actual production Runtime/Store SQLite with synthetic action durations.
"""
import json
from pathlib import Path
import tempfile
import time
import unittest

from v13.runtime import Runtime
from v13.store import Store
from v13 import world_model as W


class EventGroupHoldoutRun301(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")

    def tearDown(self):
        if self.r is not None:
            self.r.close()
        self.temp.cleanup()

    def build(self, event_count, actions_per_event):
        for i in range(event_count):
            text = f"World grouped event {i} with observed actions"
            event = self.r.store.event(self.r.session, text)
            for j in range(actions_per_event):
                route = W.ACTIONS[(i * actions_per_event + j) % len(W.ACTIONS)]
                with self.r.store.tx() as c:
                    c.execute(
                        "INSERT INTO packets VALUES (?,?,?,?,?,?)",
                        (f"run301-route-{i}-{j}", "ActionSelection", event["event_id"],
                         event["brain_generation_id"],
                         json.dumps({"route_hint": route}), time.time()),
                    )
                aid = self.r.store.start_action(
                    event["event_id"], event["brain_generation_id"],
                    forecast={"input_chars": len(text), "resource_state": "NORMAL",
                              "profile": {"role": "C3_LANGUAGE"}},
                )
                self.r.store.finish_action(
                    aid, "FINAL",
                    {"action_duration_s": 0.5 + i * .12 + j * .03,
                     "characters": 30 + i + j, "role": "C3_LANGUAGE"},
                )

    def test_grouped_split_is_disjoint_and_unique_case_unchanged(self):
        groups = [f"e{i//2}" for i in range(24)]
        train, held = W._split(24, groups)
        self.assertTrue(train and held)
        self.assertFalse({groups[i] for i in train} & {groups[i] for i in held})
        unique = [f"e{i}" for i in range(24)]
        self.assertEqual(W._split(24, unique), W._split(24))

    def test_real_source_bound_multi_action_event_fit_and_restart(self):
        self.build(12, 2)
        rows = W.transitions(self.r.store)
        self.assertEqual(len(rows), 24)
        groups = [row["event_id"] for row in rows]
        self.assertEqual(len(set(groups)), 12)
        train, held = W._split(len(rows), groups)
        self.assertFalse({groups[i] for i in train} & {groups[i] for i in held})
        state = W.fit(self.r.store, rng_seed=301)
        self.assertEqual(state["status"], "FITTED", state.get("status"))
        self.assertEqual(state["n"], 24)
        metrics = state["metrics"]
        self.assertEqual(metrics["group_split"], "EVENT_DISJOINT")
        self.assertTrue(metrics["group_disjoint"])
        self.assertEqual(metrics["train_group_count"] + metrics["held_out_group_count"], 12)
        self.assertEqual(metrics["held_out"], len(held))
        self.assertIsNotNone(W.load(self.r.store))
        self.r.close()
        self.r = None
        fresh = Store(self.home)
        try:
            self.assertIsNotNone(W.load(fresh))
        finally:
            fresh.close()

    def test_one_event_cannot_forge_heldout_score(self):
        self.build(1, 24)
        rows = W.transitions(self.r.store)
        self.assertEqual(len(rows), 24)
        self.assertEqual(len({r["event_id"] for r in rows}), 1)
        state = W.fit(self.r.store, rng_seed=301)
        self.assertEqual(state["status"], "INSUFFICIENT_INDEPENDENT_GROUPS")
        self.assertIsNone(W.load(self.r.store))


if __name__ == "__main__":
    unittest.main()
