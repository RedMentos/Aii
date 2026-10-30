"""Run13E real Context OS SOURCE_LINKS -> exact Store/JEF SHADOW bridge."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts import c2_body_disjoint_paired181_run11v as frozen
from scripts.c2_body_run12n_fulltask_readonly import explicit_faster_claim
from v13 import context_os as C
from v13.agi.context_source_link_budget_run13e import propose_pointer
from v13.runtime import Runtime

CASE = {
    "project": "Beacon211", "budget": 487,
    "a": "Cedar", "a_cost": 318, "a_days": 6,
    "b": "Quartz", "b_cost": 429, "b_days": 2,
}
LONG = "A long unrelated note about garden soil and weather. " * 8


def query():
    return "Calculate both remaining budgets and faster option for Project Beacon211."


def prepare(runtime, *, foreign_source=False):
    store = runtime.store
    if foreign_source:
        other = store.new_session("other")
        source_event = store.event(other, frozen.prompt(CASE))["event_id"]
    else:
        source_event = store.event(runtime.session, frozen.prompt(CASE))["event_id"]
    history = [
        {"event_id": source_event, "role": "user", "text": frozen.prompt(CASE)},
        {"event_id": source_event, "role": "assistant", "text": "Not yet answered."},
    ]
    fillers = []
    for i in range(5):
        content = f"Garden note {i}. " + LONG
        event = store.event(runtime.session, content)["event_id"]
        fillers.append(event)
        history.extend([
            {"event_id": event, "role": "user", "text": content},
            {"event_id": event, "role": "assistant", "text": "No answer. " + LONG},
        ])
    query_event = store.event(runtime.session, query())["event_id"]
    cfg = dict(runtime.cfg, context_tokens=600, answer_tokens=64)
    plan = C.ContextOS(store, cfg).plan(
        query_event, "C3_LANGUAGE", "SYS", [], history, query())
    return source_event, query_event, plan, fillers


class Run13EContextSourceLink(unittest.TestCase):
    def test_real_source_pointer_resolves_exact_answer_without_model(self):
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                runtime.sleep.cycle.set_policy("enabled", "off")
                source, qevent, plan, _ = prepare(runtime)
                items = [x for x in plan["plan"]["items"]
                         if x.get("item_id") == source]
                self.assertEqual(len(items), 1)
                self.assertEqual(items[0]["layer"], "SOURCE_LINKS")
                self.assertEqual(items[0]["form"], "POINTER")
                self.assertEqual(plan["plan"]["mode"], "SHADOW")
                self.assertFalse(plan["applied"])
                before = runtime.store.one(
                    "SELECT count(*) AS n FROM sources")["n"]
                with patch.object(runtime.pool, "get",
                                  side_effect=AssertionError("NATIVE_MODEL_CALLED")):
                    got = propose_pointer(runtime.store, plan["packet_id"],
                                          qevent, source)
                after = runtime.store.one(
                    "SELECT count(*) AS n FROM sources")["n"]
                self.assertEqual(before, after)
                self.assertEqual(got["source_event_id"], source)
                self.assertEqual(got["context_plan_packet_id"], plan["packet_id"])
                self.assertEqual(got["status"], "SHADOW_NO_AUTHORITY")
                self.assertEqual(got["authority"], 0)
                self.assertEqual(got["delivery_authority"], 0)
                self.assertEqual(got["native_calls"], 0)
                self.assertEqual(got["learning_mode"], "RECORD_ONLY")
                self.assertEqual(got["step2_status"], "UTILITY_FAIL")
                self.assertEqual(got["jepa_weight"], 0)
                self.assertEqual(frozen.score_pair(CASE, got["answer"])["correct"], 2)
                self.assertEqual(explicit_faster_claim(
                    got["answer"], CASE["a"], CASE["b"]), "Quartz")
            finally:
                runtime.close()

    def test_wrong_packet_and_nonpointer_source_abstain(self):
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                source, qevent, plan, fillers = prepare(runtime)
                for packet_id, event_id in (
                    ("not-a-packet", source),
                    (plan["packet_id"], fillers[-1]),
                    (plan["packet_id"], qevent),
                ):
                    got = propose_pointer(runtime.store, packet_id, qevent, event_id)
                    self.assertIsNone(got["answer"])
                    self.assertEqual(got["delivery_authority"], 0)
            finally:
                runtime.close()

    def test_cross_session_and_deleted_source_abstain(self):
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                source, qevent, plan, _ = prepare(runtime, foreign_source=True)
                self.assertIsNone(propose_pointer(
                    runtime.store, plan["packet_id"], qevent, source)["answer"])
            finally:
                runtime.close()
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                source, qevent, plan, _ = prepare(runtime)
                with runtime.store.tx() as db:
                    db.execute("UPDATE sources SET deleted=1 WHERE id="
                               "(SELECT source_id FROM events WHERE id=?)",
                               (source,))
                self.assertIsNone(propose_pointer(
                    runtime.store, plan["packet_id"], qevent, source)["answer"])
            finally:
                runtime.close()

    def test_persisted_duplicate_pointer_or_event_mismatch_abstains(self):
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                source, qevent, plan, _ = prepare(runtime)
                payload = dict(plan["plan"])
                pointer = next(x for x in payload["items"]
                               if x.get("item_id") == source)
                payload["items"] = list(payload["items"]) + [dict(pointer)]
                with runtime.store.tx() as db:
                    db.execute("UPDATE packets SET payload=? WHERE id=?",
                               (json.dumps(payload), plan["packet_id"]))
                self.assertIsNone(propose_pointer(
                    runtime.store, plan["packet_id"], qevent, source)["answer"])
                with runtime.store.tx() as db:
                    db.execute("UPDATE packets SET event_id=? WHERE id=?",
                               ("foreign-event", plan["packet_id"]))
                self.assertIsNone(propose_pointer(
                    runtime.store, plan["packet_id"], qevent, source)["answer"])
            finally:
                runtime.close()


if __name__ == "__main__":
    unittest.main()
