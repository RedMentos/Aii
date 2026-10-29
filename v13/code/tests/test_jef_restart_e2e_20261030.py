"""JEF operator integration: delivered FINAL and actual SQLite restart."""
import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from v13.runtime import Runtime
from v13.operator import Operator
from v13.contracts import packet
from v13 import jefbridge as J


class JEFRestartE2ETests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def test_real_delivered_final_accepts_operator_feedback(self):
        def gen(messages, *args, **kwargs):
            yield "fine"
        self.r._route = Mock(return_value=("simple", {"source": "TEST_ROUTE_SEAM"}))
        self.r.pool.get = Mock(return_value=SimpleNamespace(
            role="C3_LANGUAGE", last_metrics={}, generate=gen))
        self.r.learner.output_delta = Mock(return_value=None)
        self.r.submit("A simple delivered test message")
        deadline = time.monotonic() + 10
        while not self.r.idle() and time.monotonic() < deadline:
            time.sleep(0.005)
        last = self.r.last_answer()
        self.assertIsNotNone(last)
        self.assertEqual(last["status"], "FINAL")
        op = Operator(self.r)
        jef = json.loads(op.run(":jef last"))
        self.assertEqual(jef["event_id"], last["event_id"])
        feedback = json.loads(op.run(
            f":jef outcome {last['event_id']} 0.8"))
        self.assertEqual(feedback, {"updated_offers": 0})
        self.assertEqual(self.r.cfg["learning_mode"], "RECORD_ONLY")

    def test_duplicate_receipt_and_chat_scope_survive_actual_restart(self):
        j = J.controller(self.r)
        e = self.r.store.event(self.r.session, "RESTART_SELECTED_OFFER")
        eid = e["event_id"]
        ev = {"event_id": eid,
              "brain_generation_id": self.r.store.generation_id,
              "source_ref": self.r.store.source("RESTART_SELECTED_OFFER")}
        offer = self.r.store.add_packet("OfferPacket", packet(
            "OfferPacket", "B1_DETAIL", eid, ev["brain_generation_id"],
            [ev["source_ref"]], role="B1_DETAIL",
            based_on_state_version=1, deadline_monotonic_ns=1,
            evidence_refs=[ev["source_ref"]],
            offer={"summary": "RESTART_SELECTED_OFFER", "quotes": [],
                   "uncertainty": "", "needs_reentry": False},
            confidence=0.7))
        j.learn_turn(ev, "RESTART_SELECTED_OFFER", [offer],
                     "RESTART_SELECTED_OFFER",
                     {"coalition": [{"item_id": offer["packet_id"]}],
                      "inquisition": [], "decision": "INCORPORATE_A"},
                     [offer["packet_id"]])
        self.r.store.message(self.r.session, eid, "assistant",
                             "RESTART_SELECTED_OFFER", status="FINAL")
        self.assertEqual(json.loads(
            Operator(self.r).run(f":jef outcome {eid} 0.8")),
            {"updated_offers": 1})
        old_session = self.r.session
        old_state = self.r.store.state(J.KEY)[0]
        self.r.close()

        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.assertNotEqual(self.r.session, old_session)
        self.assertEqual(self.r.store.state(J.KEY)[0], old_state)
        self.assertEqual(J.controller(self.r).outcome(eid, 0.8),
                         {"updated_offers": 0})
        self.assertEqual(self.r.store.state(J.KEY)[0], old_state)
        op = Operator(self.r)
        self.assertIsNone(json.loads(op.run(":jef last")))
        with self.assertRaisesRegex(ValueError, "CURRENT_SESSION_EVENT_REQUIRED"):
            op.run(f":jef outcome {eid} 0.8")
        self.assertEqual(self.r.pool.pids(), [])


if __name__ == "__main__":
    unittest.main()
