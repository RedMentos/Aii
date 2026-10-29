"""N3 JEF explicit feedback requires a delivered assistant FINAL, not a provisional turn."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.runtime import Runtime
from v13.operator import Operator
from v13.contracts import packet
from v13 import jefbridge as J


class JEFFinalFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.j = J.controller(self.r)
        self.op = Operator(self.r)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def turn(self, session, text, status=None, role="assistant"):
        e = self.r.store.event(session, text)
        eid = e["event_id"]
        event = {"event_id": eid,
                 "brain_generation_id": self.r.store.generation_id,
                 "source_ref": self.r.store.source(text)}
        offer = self.r.store.add_packet("OfferPacket", packet(
            "OfferPacket", "B1_DETAIL", eid, event["brain_generation_id"],
            [event["source_ref"]], role="B1_DETAIL",
            based_on_state_version=1, deadline_monotonic_ns=1,
            evidence_refs=[event["source_ref"]],
            offer={"summary": text, "quotes": [], "uncertainty": "",
                   "needs_reentry": False}, confidence=0.7))
        self.j.learn_turn(
            event, text, [offer], text,
            {"coalition": [{"item_id": offer["packet_id"]}],
             "inquisition": [], "decision": "INCORPORATE_A"},
            [offer["packet_id"]])
        if status is not None:
            self.r.store.message(session, eid, role, text, status=status)
        return eid

    def test_absent_or_nonfinal_answer_refuses_before_sgd(self):
        cases = (None, "DRAFT", "OUTPUT_COMMITTED", "CANCELLED", "ERROR")
        for status in cases:
            with self.subTest(status=status):
                eid = self.turn(self.r.session, f"PROVISIONAL_{status}", status)
                before = self.r.store.state(J.KEY)[0]
                with patch.object(J.JEFBridge, "outcome",
                                  side_effect=AssertionError("nonfinal trained")):
                    with self.assertRaisesRegex(
                            ValueError, "FINAL_ANSWER_REQUIRED"):
                        self.op.run(f":jef outcome {eid} 0.8")
                self.assertEqual(self.r.store.state(J.KEY)[0], before)

    def test_final_user_message_is_not_assistant_final(self):
        eid = self.turn(self.r.session, "USER_FINAL_ONLY",
                        status="FINAL", role="user")
        before = self.r.store.state(J.KEY)[0]
        with self.assertRaisesRegex(ValueError, "FINAL_ANSWER_REQUIRED"):
            self.op.run(f":jef outcome {eid} 0.8")
        self.assertEqual(self.r.store.state(J.KEY)[0], before)

    def test_foreign_final_remains_refused_by_session(self):
        other = self.r.store.new_session()
        eid = self.turn(other, "FOREIGN_FINAL", status="FINAL")
        before = self.r.store.state(J.KEY)[0]
        with self.assertRaisesRegex(ValueError, "CURRENT_SESSION_EVENT_REQUIRED"):
            self.op.run(f":jef outcome {eid} 0.8")
        self.assertEqual(self.r.store.state(J.KEY)[0], before)

    def test_current_final_updates_once_and_remains_age0(self):
        eid = self.turn(self.r.session, "OWN_FINAL", status="FINAL")
        before = self.j.report()["updates"]
        self.assertEqual(json.loads(self.op.run(f":jef outcome {eid} 0.8")),
                         {"updated_offers": 1})
        self.assertEqual(json.loads(self.op.run(f":jef outcome {eid} 0.8")),
                         {"updated_offers": 0})
        self.assertEqual(self.j.report()["updates"], before + 1)
        self.assertEqual(self.r.cfg["system_stage"], 0)
        self.assertEqual(self.r.cfg["learning_mode"], "RECORD_ONLY")
        self.assertEqual(self.r.pool.pids(), [])


if __name__ == "__main__":
    unittest.main()
