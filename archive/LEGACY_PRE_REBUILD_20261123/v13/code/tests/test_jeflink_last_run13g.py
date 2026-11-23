"""Run13G bounded unique-only :jeflink last operator integration."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts import c2_body_disjoint_paired181_run11v as frozen
from tests.test_context_source_link_budget_run13e import CASE, prepare
from v13.operator import Operator
from v13.runtime import Runtime


def rewrite_packet(store, packet_id, transform):
    row = store.one("SELECT payload FROM packets WHERE id=?", (packet_id,))
    data = json.loads(row["payload"])
    transform(data)
    with store.tx() as db:
        db.execute("UPDATE packets SET payload=? WHERE id=?",
                   (json.dumps(data), packet_id))


class Run13GJeflinkLast(unittest.TestCase):
    def test_one_command_uses_unique_verified_pointer_without_chat_or_native(self):
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                runtime.sleep.cycle.set_policy("enabled", "off")
                source, query, plan, _ = prepare(runtime)
                op = Operator(runtime)
                before = runtime.store.one(
                    "SELECT count(*) AS n FROM sources")["n"]
                messages = runtime.store.one(
                    "SELECT count(*) AS n FROM messages WHERE role='assistant'")["n"]
                with patch.object(runtime.pool, "get",
                                  side_effect=AssertionError("NATIVE_MODEL_CALLED")):
                    got = json.loads(op.run(":jeflink last"))
                    explicit = json.loads(op.run(
                        f":jeflink {plan['packet_id']} {query} {source}"))
                self.assertEqual(got["answer"], explicit["answer"])
                self.assertIn("Cedar leaves 169 Euro remaining.", got["answer"])
                self.assertIn("Quartz leaves 58 Euro remaining.", got["answer"])
                self.assertIn("Quartz finishes sooner.", got["answer"])
                self.assertEqual(got["delivery_authority"], 0)
                self.assertEqual(got["native_calls"], 0)
                self.assertTrue(got["operator_diagnostic"])
                self.assertTrue(got["not_chat_turn"])
                self.assertEqual(before, runtime.store.one(
                    "SELECT count(*) AS n FROM sources")["n"])
                self.assertEqual(messages, runtime.store.one(
                    "SELECT count(*) AS n FROM messages WHERE role='assistant'")["n"])
            finally:
                runtime.close()

    def test_two_matching_pointers_fail_closed_without_first_match_shortcut(self):
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                duplicate = runtime.store.event(
                    runtime.session, frozen.prompt(CASE))["event_id"]
                source, query, plan, _ = prepare(runtime)
                def add(data):
                    data["items"].append({
                        "item_id": duplicate, "layer": "SOURCE_LINKS",
                        "form": "POINTER", "chars": 0,
                    })
                rewrite_packet(runtime.store, plan["packet_id"], add)
                got = json.loads(Operator(runtime).run(":jeflink last"))
                self.assertEqual(got["reason"], "MULTIPLE_VERIFIED_SOURCE_LINKS")
                self.assertIsNone(got["answer"])
                self.assertEqual(got["delivery_authority"], 0)
            finally:
                runtime.close()

    def test_overlimit_duplicate_and_nonshadow_plans_abstain(self):
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                source, query, plan, _ = prepare(runtime)
                def many(data):
                    for i in range(33):
                        data["items"].append({
                            "item_id": "evt_" + f"{i:032x}",
                            "layer": "SOURCE_LINKS", "form": "POINTER",
                        })
                rewrite_packet(runtime.store, plan["packet_id"], many)
                got = json.loads(Operator(runtime).run(":jeflink last"))
                self.assertIsNone(got["answer"])
                self.assertEqual(got["reason"],
                                 "SOURCE_LINK_SET_EMPTY_AMBIGUOUS_OR_OVERSIZE")
                def active(data):
                    data["mode"] = "ACTIVE"
                    data["applied"] = True
                rewrite_packet(runtime.store, plan["packet_id"], active)
                got = json.loads(Operator(runtime).run(":jeflink last"))
                self.assertIsNone(got["answer"])
                self.assertEqual(got["reason"], "CONTEXT_PLAN_NOT_SHADOW_BOUND")
            finally:
                runtime.close()

    def test_no_plan_and_other_session_never_leak(self):
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                op = Operator(runtime)
                got = json.loads(op.run(":jeflink last"))
                self.assertEqual(got["reason"], "NO_CURRENT_SESSION_CONTEXT_PLAN")
                self.assertIsNone(got["answer"])
                prepare(runtime)
                runtime.session = runtime.store.new_session("new")
                got = json.loads(op.run(":jeflink last"))
                self.assertEqual(got["reason"], "NO_CURRENT_SESSION_CONTEXT_PLAN")
                self.assertIsNone(got["answer"])
                with self.assertRaises(ValueError):
                    op.run(":jeflink last", origin="REMOTE")
            finally:
                runtime.close()


if __name__ == "__main__":
    unittest.main()
