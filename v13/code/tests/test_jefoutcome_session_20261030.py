"""N3/WP-U1: operator lifecycle is scoped to the current chat, including restart."""
import json
import tempfile
import unittest
from pathlib import Path

from v13.contracts import packet
from v13.operator import Operator
from v13.runtime import Runtime
from v13 import jefoutcome as jo


class LifecycleSessionBoundary(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.op = Operator(self.r)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def experience(self, text):
        e = self.r.store.event(self.r.session, text)
        self.r.store.add_packet("ExperienceRecord", packet(
            "ExperienceRecord", "C1_EXEC", e["event_id"],
            e["brain_generation_id"], [e["source_ref"]],
            source_ref=e["source_ref"],
            self_candidate_hash="0" * 64, outcome="FINAL"))
        return e["event_id"]

    def summary(self):
        return json.loads(self.op.run(":fastpolicy lifecycle"))

    def test_direct_and_operator_refuse_foreign_event_without_stage_leak(self):
        first = self.r.session
        a = self.experience("private lifecycle in first chat")
        self.assertEqual(jo.lifecycle(self.r, a)["stage"], "L0_CAPTURE")
        self.assertEqual(self.summary()["experiences"], 1)
        second = self.op.run(":new")
        b = self.experience("second chat experience")
        self.assertNotEqual(first, second)
        self.assertEqual(jo.lifecycle(self.r, b)["stage"], "L0_CAPTURE")
        for call in (lambda: jo.lifecycle(self.r, a),
                     lambda: self.op.run(f":fastpolicy lifecycle {a}")):
            with self.assertRaisesRegex(ValueError, "CURRENT_SESSION_EVENT_REQUIRED"):
                call()
        self.assertEqual(self.summary()["experiences"], 1)
        self.assertEqual(self.summary()["by_stage"], {"L0_CAPTURE": 1})
        self.assertEqual(self.op.run(f":open {first}"), first)
        self.assertEqual(self.summary()["experiences"], 1)
        with self.assertRaisesRegex(ValueError, "CURRENT_SESSION_EVENT_REQUIRED"):
            self.op.run(f":fastpolicy lifecycle {b}")

    def test_limit_is_applied_after_session_filter_not_global_scan(self):
        first = self.r.session
        own = self.experience("own older event")
        second = self.op.run(":new")
        for i in range(3):
            self.experience(f"foreign recent event {i}")
        self.assertEqual(self.summary()["experiences"], 3)
        self.op.run(f":open {first}")
        self.assertEqual(jo.lifecycle_summary(self.r, limit=1),
                         {"experiences": 1, "by_stage": {"L0_CAPTURE": 1}})
        self.assertEqual(self.summary()["experiences"], 1)
        self.assertEqual(self.op.run(f":fastpolicy lifecycle {own}")[:1], "{")
        with self.assertRaisesRegex(ValueError, "CURRENT_SESSION_EVENT_REQUIRED"):
            jo.lifecycle(self.r, "evt_missing")

    def test_new_empty_chat_and_sqlite_restart_remain_isolated(self):
        first = self.r.session
        a = self.experience("first chat only")
        second = self.op.run(":new")
        self.assertEqual(self.summary(), {"experiences": 0, "by_stage": {}})
        b = self.experience("second chat only")
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.op = Operator(self.r)
        self.assertEqual(self.r.session, second)
        self.assertEqual(self.summary()["experiences"], 1)
        with self.assertRaisesRegex(ValueError, "CURRENT_SESSION_EVENT_REQUIRED"):
            self.op.run(f":fastpolicy lifecycle {a}")
        self.assertEqual(jo.lifecycle(self.r, b)["stage"], "L0_CAPTURE")
        self.op.run(f":open {first}")
        self.assertEqual(self.summary()["experiences"], 1)
        with self.assertRaisesRegex(ValueError, "CURRENT_SESSION_EVENT_REQUIRED"):
            jo.lifecycle(self.r, b)
        self.assertEqual(self.r.pool.pids(), [])


if __name__ == "__main__":
    unittest.main()
