"""Run99: B3 channel utility requires the receiver's explicit peer-message link.

SOURCE_EXACT/CONTROL/SYMBOLIC messages may earn utility only when the
receiver OfferPacket identifies the exact MessagePacket it consumed.
NO_MESSAGE is the intentionally unlinked control baseline.
"""
import time

from v13.contracts import packet
from tests.test_callosum import Base


class CallosumPeerLinkRun99(Base):
    def event(self):
        return self.r.store.event(self.r.session, "Compare 08:15 and 09:40")

    def message(self, event, channel="SOURCE_EXACT"):
        refs = [event["source_ref"]] if channel == "SOURCE_EXACT" else []
        p = packet("MessagePacket", "B3_CALLOSUM",
                   event["event_id"], event["brain_generation_id"], refs,
                   sender="B1_DETAIL", receiver="B2_GIST", channel=channel,
                   source_refs=refs, content={"quotes": []})
        return self.r.store.add_packet("MessagePacket", p)

    def offer(self, event, peer_id=None):
        p = packet(
            "OfferPacket", "B2_GIST", event["event_id"],
            event["brain_generation_id"], [event["source_ref"]],
            role="B2_GIST", based_on_state_version=1,
            deadline_monotonic_ns=time.monotonic_ns() + 10**9,
            evidence_refs=[event["source_ref"]],
            offer={"summary": "source bound", "quotes": [], "uncertainty": "",
                   "needs_reentry": False}, confidence=0.8,
            peer_message_packet_id=peer_id,
        )
        return self.r.store.add_packet("OfferPacket", p)

    def note(self, event, msg, channel="SOURCE_EXACT"):
        self.c.note(event["event_id"], msg["packet_id"],
                    "B1_DETAIL", "B2_GIST", channel, channel, False, 0.)

    def test_unlinked_receiver_offer_cannot_credit_source_exact_message(self):
        event = self.event()
        msg = self.message(event)
        self.note(event, msg)
        offer = self.offer(event, peer_id=None)
        result = self.c.outcome(event["event_id"], [offer["packet_id"]], "FINAL")
        self.assertEqual(result["scored"], 0)

    def test_offer_link_to_different_message_cannot_credit_pending_message(self):
        event = self.event()
        msg = self.message(event)
        self.note(event, msg)
        offer = self.offer(event, peer_id="pkt_unrelated")
        result = self.c.outcome(event["event_id"], [offer["packet_id"]], "FINAL")
        self.assertEqual(result["scored"], 0)

    def test_exact_peer_link_credits_once(self):
        event = self.event()
        msg = self.message(event)
        self.note(event, msg)
        offer = self.offer(event, peer_id=msg["packet_id"])
        self.assertEqual(
            self.c.outcome(event["event_id"], [offer["packet_id"]], "FINAL")["scored"], 1
        )
        self.assertEqual(
            self.c.outcome(event["event_id"], [offer["packet_id"]], "FINAL")["scored"], 0
        )

    def test_unlinked_no_message_control_baseline_remains_measurable(self):
        event = self.event()
        msg = self.message(event, channel="NO_MESSAGE")
        self.note(event, msg, channel="NO_MESSAGE")
        offer = self.offer(event, peer_id=None)
        result = self.c.outcome(event["event_id"], [offer["packet_id"]], "FINAL")
        self.assertEqual(result["scored"], 1)
        self.assertEqual(self.c._load()[0]["dirs"]["B1_TO_B2"]["u"]["NO_MESSAGE"]["n"], 1)

    def test_first_unlinked_offer_does_not_hide_later_linked_offer(self):
        event = self.event()
        msg = self.message(event)
        self.note(event, msg)
        self.offer(event, peer_id=None)
        linked = self.offer(event, peer_id=msg["packet_id"])
        result = self.c.outcome(event["event_id"], [linked["packet_id"]], "FINAL")
        self.assertEqual(result["scored"], 1)
        self.assertGreater(result["utilities"][0], 1.5)


if __name__ == "__main__":
    import unittest
    unittest.main()
