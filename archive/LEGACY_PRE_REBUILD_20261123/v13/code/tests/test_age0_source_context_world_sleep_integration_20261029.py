"""One-home Age0 operator smoke: verified F1/F5 source, N7, T8 and G13."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.runtime import Runtime
from v13.operator import Operator
from v13 import context_os as C
from v13 import world_model as WM


class Age0CrossOrganSourceWorldSleepTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.op = Operator(self.r)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def test_one_home_readonly_crossorgan_path_without_native_or_learning(self):
        with patch.object(self.r.pool, "get",
                          side_effect=AssertionError("native model must not load")):
            recorded = json.loads(
                self.op.run(":source budget Elyra 615 --confirm"))
            self.assertEqual(recorded["status"], "RECORDED_VERIFIED")
            self.assertEqual(recorded["permission"], "record")
            self.assertEqual(recorded["scope"], "session")
            self.assertFalse(recorded["model_called"])

            exact = json.loads(self.op.run(
                ":verified exact What is the budget for Project Elyra?"))
            self.assertEqual(exact["status"], "FINAL_SOURCE_EXACT")
            self.assertEqual(exact["answer"], "Project Elyra: 615 Euro.")
            self.assertFalse(exact["model_called"])
            self.assertEqual(exact["native_calls"], 0)
            self.assertFalse(exact["learned"])

            event = self.r.store.event(
                self.r.session, "CURRENT_SESSION_CONTEXT_PLAN")
            C.controller(self.r).plan(
                event["event_id"], "C3_LANGUAGE", "SYS", [], [],
                "CURRENT_SESSION_CONTEXT_PLAN")
            last = json.loads(self.op.run(":ctxos last"))
            self.assertEqual(last["event_id"], event["event_id"])

            observed = self.r.store.event(
                self.r.session, "Observed local action for T8")
            action = self.r.store.start_action(
                observed["event_id"], observed["brain_generation_id"],
                forecast={"input_chars":80, "resource_state":"NORMAL"})
            self.r.store.finish_action(
                action, "FINAL",
                {"action_duration_s":1.25, "characters":35})
            recent = json.loads(self.op.run(":worldmodel recent"))
            self.assertIn(observed["event_id"], recent["events"])
            before_world = self.r.store.state(WM.KEY)
            before_actions = self.r.store.one(
                "SELECT COUNT(*) AS n FROM actions")["n"]
            compared = json.loads(self.op.run(
                ":worldmodel compare " + observed["event_id"]))
            self.assertFalse(compared["decision_authority"])
            self.assertFalse(compared["ranked"])
            self.assertEqual(set(compared["routes"]), set(WM.ACTIONS))
            for cf in compared["routes"].values():
                self.assertEqual(cf["reason"], "NO_WORLD_MODEL")
                self.assertEqual(cf["label"], "SIMULATION_UNCERTAIN")
                self.assertIsNone(cf["prediction"])
                self.assertEqual(cf["confidence"], 0.)
            self.assertEqual(self.r.store.state(WM.KEY), before_world)
            self.assertEqual(self.r.store.one(
                "SELECT COUNT(*) AS n FROM actions")["n"], before_actions)

            before_queue = self.r.sleep.scheduler.report()
            with self.assertRaises(ValueError):
                self.op.run(":sleep in nan")
            self.assertEqual(self.r.sleep.scheduler.report(), before_queue)

        self.assertEqual(self.r.cfg["system_stage"], 0)
        self.assertEqual(self.r.cfg["learning_mode"], "RECORD_ONLY")
        self.assertIs(self.r.cfg["latents_enabled"], False)
        self.assertEqual(self.r.cfg.get("jepa_weight", 0), 0)
        self.assertEqual(self.r.pool.pids(), [])


if __name__ == "__main__":
    unittest.main()
