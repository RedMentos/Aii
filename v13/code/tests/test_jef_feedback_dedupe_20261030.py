"""N3 JEF identical human feedback is applied once per retained event/source."""
import json
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.operator import Operator
from v13.contracts import packet
from v13 import jefbridge as J


class JEFHumanReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.j = J.controller(self.r)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def turn(self, text):
        e = self.r.store.event(self.r.session, text)
        eid = e["event_id"]
        event = {
            "event_id": eid,
            "brain_generation_id": self.r.store.generation_id,
            "source_ref": self.r.store.source(text),
        }
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
        self.r.store.message(self.r.session, eid, "assistant",
                             text, status="FINAL")
        return eid

    def test_exact_duplicate_is_noop_and_survives_new_controller(self):
        eid = self.turn("ONE_RECEIPT")
        self.assertEqual(self.j.outcome(eid, 0.8), {"updated_offers": 1})
        first = self.r.store.state(J.KEY)[0]
        self.assertEqual(self.j.outcome(eid, 0.8), {"updated_offers": 0})
        self.assertEqual(self.r.store.state(J.KEY)[0], first)
        restarted = J.JEFBridge(self.r.store, self.r.cfg)
        self.assertEqual(restarted.outcome(eid, 0.8), {"updated_offers": 0})
        self.assertEqual(self.r.store.state(J.KEY)[0], first)

    def test_changed_utility_is_new_online_update_not_gradient_reversal(self):
        eid = self.turn("REVISED_RECEIPT")
        self.assertEqual(self.j.outcome(eid, 0.8)["updated_offers"], 1)
        before = self.j.report()["updates"]
        self.assertEqual(self.j.outcome(eid, 0.6)["updated_offers"], 1)
        self.assertEqual(self.j.report()["updates"], before + 1)
        self.assertEqual(self.j.outcome(eid, 0.6)["updated_offers"], 0)
        receipts = self.r.store.state(J.KEY)[0]["outcome_receipts"]
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0]["utility"], 0.6)

    def test_same_rating_on_distinct_events_is_not_deduplicated(self):
        a = self.turn("FIRST_EVENT")
        b = self.turn("SECOND_EVENT")
        before = self.j.report()["updates"]
        self.assertEqual(self.j.outcome(a, 0.5)["updated_offers"], 1)
        self.assertEqual(self.j.outcome(b, 0.5)["updated_offers"], 1)
        self.assertEqual(self.j.report()["updates"], before + 2)
        self.assertEqual(len(self.r.store.state(J.KEY)[0]["outcome_receipts"]), 2)

    def test_receipts_expire_with_retained_turn_window(self):
        oldest = self.turn("OLD_TURN")
        self.assertEqual(self.j.outcome(oldest, 0.8)["updated_offers"], 1)
        for i in range(J.TURNS_KEEP):
            self.turn(f"NEW_TURN_{i}")
        st = self.r.store.state(J.KEY)[0]
        self.assertEqual(len(st["turns"]), J.TURNS_KEEP)
        self.assertFalse(any(x["event_id"] == oldest
                             for x in st["outcome_receipts"]))
        before = self.j.report()["updates"]
        self.assertEqual(self.j.outcome(oldest, 0.8)["updated_offers"], 0)
        self.assertEqual(self.j.report()["updates"], before)

    def test_operator_repeated_current_chat_feedback_is_exact_once(self):
        eid = self.turn("OPERATOR_FEEDBACK")
        op = Operator(self.r)
        before = self.j.report()["updates"]
        self.assertEqual(json.loads(op.run(f":jef outcome {eid} 0.8")),
                         {"updated_offers": 1})
        self.assertEqual(json.loads(op.run(f":jef outcome {eid} 0.8")),
                         {"updated_offers": 0})
        self.assertEqual(self.j.report()["updates"], before + 1)
        self.assertEqual(self.r.cfg["learning_mode"], "RECORD_ONLY")
        self.assertEqual(self.r.pool.pids(), [])


if __name__ == "__main__":
    unittest.main()
