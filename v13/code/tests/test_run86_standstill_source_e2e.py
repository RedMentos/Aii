"""Run86 real Age0 emergency standstill + human source preflight across restarts.

Linux software only: real Runtime, Store, Operator, ToolRegistry. No models.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13 import age as agectl
from v13 import prohibitions as P
from v13.agi.tools import ToolRegistry
from v13.operator import Operator
from v13.runtime import Runtime


class TestRun86StandstillSourceE2E(unittest.TestCase):
    def _open(self, home):
        r = Runtime(home)
        r.sleep.cycle.set_policy("enabled", "off")
        return r, Operator(r)

    def _verified(self, r, op):
        with patch.object(r.pool, "get", side_effect=AssertionError("NATIVE_MODEL_CALLED")):
            d = json.loads(op.run(":verified What is the budget for Project Elyra?"))
        self.assertEqual(d["status"], "READY")
        self.assertEqual(d["native_calls"], 0)
        self.assertFalse(d["model_called"])
        self.assertNotIn("answer", d)
        return d

    def test_human_source_and_tool_block_survive_standstill_restart(self):
        with tempfile.TemporaryDirectory(prefix="v13-run86-source-") as td:
            home = Path(td)
            r, op = self._open(home)
            try:
                self.assertEqual(json.loads(op.run(":status"))["learning"], "RECORD_ONLY")
                e = r.store.event(r.session, "Project Elyra budget")
                mid = r.memory.feedback(e["event_id"], "fact", "615 Euro",
                                        key="Project Elyra budget", permission="record")
                self.assertEqual(self._verified(r, op)["memory_id"], mid)
                self.assertIn("STILLSTAND AN", op.run(":stillstand"))
                stopped = json.loads(op.run(":stillstand json"))
                self.assertTrue(stopped["on"])
                self.assertTrue(stopped["all_parts_on"])
                self.assertTrue(stopped["confirmed_still"])
                self.assertEqual(stopped["set_by_standstill"],
                                 {"notaus": True, "queue": True, "age": True})
                reg = ToolRegistry(r.store)
                reg.enable("calc")
                self.assertEqual(reg.call("calc", {"expression": "1+1"},
                                          origin="USER")["reason"], "HARD_BLOCK:NOTAUS")
                with self.assertRaisesRegex(ValueError, "RUNTIME_NOT_IDLE"):
                    self._verified(r, op)
            finally:
                r.close()

            r, op = self._open(home)
            try:
                stopped = json.loads(op.run(":stillstand json"))
                self.assertTrue(stopped["on"])
                self.assertTrue(stopped["all_parts_on"])
                self.assertTrue(r.paused)
                self.assertTrue(P.report(r.store)["notaus"])
                self.assertTrue(agectl.controller(r).view()["frozen"])
                with self.assertRaisesRegex(ValueError, "RUNTIME_NOT_IDLE"):
                    self._verified(r, op)
                self.assertIn("aufgehoben", op.run(":stillstand aus"))
                self.assertEqual(self._verified(r, op)["memory_id"], mid)
                self.assertFalse(json.loads(op.run(":stillstand json"))["on"])
                self.assertFalse(r.paused)
                self.assertFalse(P.report(r.store)["notaus"])
                self.assertFalse(agectl.controller(r).view()["frozen"])
                self.assertEqual(json.loads(op.run(":status"))["learning"], "RECORD_ONLY")
            finally:
                r.close()

            r, op = self._open(home)
            try:
                self.assertFalse(json.loads(op.run(":stillstand json"))["on"])
                self.assertEqual(self._verified(r, op)["memory_id"], mid)
                self.assertEqual(json.loads(op.run(":status"))["learning"], "RECORD_ONLY")
            finally:
                r.close()

    def test_release_after_restart_keeps_prior_human_notaus_and_age_freeze(self):
        with tempfile.TemporaryDirectory(prefix="v13-run86-prior-") as td:
            home = Path(td)
            r, op = self._open(home)
            try:
                op.run(":notaus")
                op.run(":age freeze on")
                self.assertTrue(P.report(r.store)["notaus"])
                self.assertTrue(agectl.controller(r).view()["frozen"])
                op.run(":stillstand")
                d = json.loads(op.run(":stillstand json"))
                self.assertTrue(d["all_parts_on"])
                self.assertEqual(d["set_by_standstill"],
                                 {"notaus": False, "queue": True, "age": False})
            finally:
                r.close()

            r, op = self._open(home)
            try:
                self.assertTrue(json.loads(op.run(":stillstand json"))["on"])
                self.assertIn("aufgehoben", op.run(":stillstand aus"))
                self.assertTrue(P.report(r.store)["notaus"])
                self.assertTrue(agectl.controller(r).view()["frozen"])
                self.assertFalse(r.paused)
                self.assertEqual(json.loads(op.run(":status"))["learning"], "RECORD_ONLY")
            finally:
                r.close()

            r, op = self._open(home)
            try:
                self.assertTrue(P.report(r.store)["notaus"])
                self.assertTrue(agectl.controller(r).view()["frozen"])
                self.assertFalse(r.paused)
                self.assertFalse(json.loads(op.run(":stillstand json"))["on"])
            finally:
                r.close()


if __name__ == "__main__":
    unittest.main()
