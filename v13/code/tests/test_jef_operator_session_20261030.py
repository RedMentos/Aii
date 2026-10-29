"""N3 JEF operator: last/outcome must stay inside the current chat."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.runtime import Runtime
from v13.operator import Operator
from v13.contracts import packet
from v13 import jefbridge as J


class JEFOperatorSessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.op = Operator(self.r)
        self.j = J.controller(self.r)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def turn(self, session, text):
        e = self.r.store.event(session, text)
        event = {
            "event_id": e["event_id"],
            "brain_generation_id": self.r.store.generation_id,
            "source_ref": self.r.store.source(text),
        }
        offer = self.r.store.add_packet("OfferPacket", packet(
            "OfferPacket", "B1_DETAIL", event["event_id"],
            event["brain_generation_id"], [event["source_ref"]],
            role="B1_DETAIL", based_on_state_version=1,
            deadline_monotonic_ns=1, evidence_refs=[event["source_ref"]],
            offer={"summary": text, "quotes": [], "uncertainty": "",
                   "needs_reentry": False}, confidence=0.8))
        self.j.learn_turn(
            event, text, [offer], text,
            {"coalition": [{"item_id": offer["packet_id"]}],
             "inquisition": [], "decision": "INCORPORATE_A"},
            [offer["packet_id"]])
        self.r.store.message(session, event["event_id"], "assistant",
                             text, status="FINAL")
        return event["event_id"]

    def test_last_returns_current_turn_even_when_foreign_is_newer(self):
        own = self.turn(self.r.session, "OWN_JEF_TURN")
        foreign_session = self.r.store.new_session()
        foreign = self.turn(foreign_session, "FOREIGN_JEF_TURN")
        with patch.object(self.r.pool, "get",
                          side_effect=AssertionError("native called")):
            got = json.loads(self.op.run(":jef last"))
        self.assertEqual(got["event_id"], own)
        self.assertNotEqual(got["event_id"], foreign)
        self.assertEqual(self.r.pool.pids(), [])

    def test_last_returns_null_with_only_foreign_turn(self):
        foreign_session = self.r.store.new_session()
        self.turn(foreign_session, "FOREIGN_ONLY_JEF_TURN")
        self.assertIsNone(json.loads(self.op.run(":jef last")))

    def test_foreign_and_unknown_outcome_refused_before_state_write(self):
        foreign_session = self.r.store.new_session()
        foreign = self.turn(foreign_session, "FOREIGN_JEF_FEEDBACK")
        before = self.r.store.state(J.KEY)
        with patch.object(J.JEFBridge, "outcome",
                          side_effect=AssertionError("foreign feedback applied")):
            for event_id in (foreign, "missing-jef-event"):
                with self.subTest(event_id=event_id):
                    with self.assertRaisesRegex(
                            ValueError, "CURRENT_SESSION_EVENT_REQUIRED"):
                        self.op.run(f":jef outcome {event_id} 1.0")
        self.assertEqual(self.r.store.state(J.KEY), before)

    def test_current_session_feedback_updates_selected_offer_once(self):
        own = self.turn(self.r.session, "OWN_JEF_FEEDBACK")
        before = self.j.report()["updates"]
        with patch.object(self.r.pool, "get",
                          side_effect=AssertionError("native called")):
            got = json.loads(self.op.run(f":jef outcome {own} 0.8"))
        self.assertEqual(got, {"updated_offers": 1})
        self.assertEqual(self.j.report()["updates"], before + 1)
        self.assertEqual(self.r.cfg["system_stage"], 0)
        self.assertEqual(self.r.cfg["learning_mode"], "RECORD_ONLY")
        self.assertIs(self.r.cfg["latents_enabled"], False)
        self.assertEqual(self.r.cfg.get("jepa_weight", 0), 0)
        self.assertEqual(self.r.pool.pids(), [])

    def test_invalid_rating_rejected_without_mutation(self):
        own = self.turn(self.r.session, "OWN_JEF_INVALID_RATING")
        before = self.r.store.state(J.KEY)
        with patch.object(J.JEFBridge, "outcome",
                          side_effect=AssertionError("invalid feedback applied")):
            for score in ("nan", "inf", "-inf", "1.01", "-0.01", "oops"):
                with self.subTest(score=score):
                    with self.assertRaisesRegex(
                            ValueError, "FINITE_0_TO_1_REQUIRED"):
                        self.op.run(f":jef outcome {own} {score}")
        self.assertEqual(self.r.store.state(J.KEY), before)


if __name__ == "__main__":
    unittest.main()
