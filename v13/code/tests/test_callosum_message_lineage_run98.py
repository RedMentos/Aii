"""Run98: B3 Callosum utility must be earned by a real, source-valid MessagePacket.

Real Runtime/SQLite packets, not model utility. Corrupt/missing or foreign
messages cannot take credit for later receiver offers.
"""
import json
import time

from v13.contracts import packet
from tests.test_callosum import Base


class CallosumMessageLineageRun98(Base):
    def event(self, text="B3 callosum source check"):
        return self.r.store.event(self.r.session, text)

    def offer(self, event, role="B2_GIST"):
        p = packet(
            "OfferPacket", role, event["event_id"], event["brain_generation_id"],
            [event["source_ref"]], role=role, based_on_state_version=1,
            deadline_monotonic_ns=time.monotonic_ns() + 10**9,
            evidence_refs=[event["source_ref"]],
            offer={"summary": "source bound", "quotes": [], "uncertainty": "",
                   "needs_reentry": False}, confidence=0.8,
        )
        return self.r.store.add_packet("OfferPacket", p)

    def message(self, event, sender="B1_DETAIL", receiver="B2_GIST"):
        p = packet(
            "MessagePacket", sender, event["event_id"],
            event["brain_generation_id"], [event["source_ref"]],
            sender=sender, receiver=receiver, channel="SOURCE_EXACT",
            source_refs=[event["source_ref"]], content={"summary": "source bound"},
        )
        return self.r.store.add_packet("MessagePacket", p)

    def note(self, event, msg_id):
        self.c.note(event["event_id"], msg_id, "B1_DETAIL", "B2_GIST",
                    "SOURCE_EXACT", "SOURCE_EXACT", False, 0.)

    def assert_uncredited(self, event, receiver):
        result = self.c.outcome(event["event_id"], [receiver["packet_id"]], "FINAL")
        self.assertEqual(result["scored"], 0)
        self.assertEqual(self.c._load()[0]["dirs"]["B1_TO_B2"]["u"], {})

    def test_missing_message_packet_never_credits_receiver_offer(self):
        event = self.event()
        self.note(event, "pkt_missing")
        receiver = self.offer(event)
        self.assert_uncredited(event, receiver)

    def test_foreign_event_message_never_credits_receiver_offer(self):
        event = self.event()
        other = self.event("unrelated source")
        msg = self.message(other)
        self.note(event, msg["packet_id"])
        receiver = self.offer(event)
        self.assert_uncredited(event, receiver)

    def test_wrong_packet_kind_never_counts_as_callosum_message(self):
        event = self.event()
        fake_msg = self.offer(event, "B1_DETAIL")
        self.note(event, fake_msg["packet_id"])
        receiver = self.offer(event)
        self.assert_uncredited(event, receiver)

    def test_wrong_sender_receiver_message_does_not_get_credit(self):
        event = self.event()
        msg = self.message(event, sender="B2_GIST", receiver="B1_DETAIL")
        self.note(event, msg["packet_id"])
        receiver = self.offer(event)
        self.assert_uncredited(event, receiver)

    def test_malformed_message_json_is_ignored_not_exception(self):
        event = self.event()
        msg = self.message(event)
        self.note(event, msg["packet_id"])
        with self.r.store.tx() as c:
            c.execute("UPDATE packets SET payload='{' WHERE id=?",
                      (msg["packet_id"],))
        receiver = self.offer(event)
        self.assert_uncredited(event, receiver)

    def test_deleted_message_source_blocks_utility_credit(self):
        event = self.event()
        msg = self.message(event)
        self.note(event, msg["packet_id"])
        with self.r.store.tx() as c:
            c.execute("UPDATE sources SET deleted=1 WHERE id=?",
                      (event["source_ref"]["source_id"],))
        receiver = self.offer(event)
        self.assert_uncredited(event, receiver)

    def test_valid_message_credits_once_and_replay_is_idempotent(self):
        event = self.event()
        msg = self.message(event)
        self.note(event, msg["packet_id"])
        receiver = self.offer(event)
        first = self.c.outcome(event["event_id"], [receiver["packet_id"]], "FINAL")
        self.assertEqual(first["scored"], 1)
        self.assertEqual(self.c._load()[0]["dirs"]["B1_TO_B2"]["u"]["SOURCE_EXACT"]["n"], 1)
        second = self.c.outcome(event["event_id"], [receiver["packet_id"]], "FINAL")
        self.assertEqual(second["scored"], 0)
        self.assertEqual(self.c._load()[0]["dirs"]["B1_TO_B2"]["u"]["SOURCE_EXACT"]["n"], 1)


if __name__ == "__main__":
    import unittest
    unittest.main()
