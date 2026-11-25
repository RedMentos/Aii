"""Tests for the staged C1-broadcast -> C5 ActionSelection provenance path."""
import json
import tempfile
import time
import unittest
from pathlib import Path

from v13 import focal
from v13.contracts import packet, validate
from v13.runtime import Runtime


class ActionSelectionBroadcastLineage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.s = self.r.store
        self.e = self.s.event(self.r.session, "Compute the total budget")

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def _broadcast(self, memory_ref, version=7):
        event_ref = self.e["source_ref"]
        refs = [event_ref, memory_ref]
        broadcast = packet(
            "JEFBroadcastPacket", "C1_EXEC", self.e["event_id"],
            self.e["brain_generation_id"], refs,
            state_version=version, goal="Compute the total budget",
            constraints=["Use admitted memory only"], source_refs=refs,
            active_task=None, memory_refs=[], open_questions=[],
            permission_flags={},
        )
        self.s.add_packet("JEFBroadcastPacket", broadcast)
        return broadcast, refs

    def _offer(self, broadcast, broadcast_id=None):
        event_ref = self.e["source_ref"]
        query = packet(
            "QueryPacket", "C1_EXEC", self.e["event_id"],
            self.e["brain_generation_id"], [event_ref],
            target_role="B1_DETAIL", goal="Compute the total budget",
            source_refs=[event_ref],
            broadcast_packet_id=broadcast["packet_id"],
            based_on_state_version=broadcast["state_version"],
            context_source_refs=[], enlightened_source_refs=[],
        )
        self.s.add_packet("QueryPacket", query)
        offer = packet(
            "OfferPacket", "B1_DETAIL", self.e["event_id"],
            self.e["brain_generation_id"], [event_ref],
            role="B1_DETAIL", based_on_state_version=broadcast["state_version"],
            deadline_monotonic_ns=int((time.monotonic() + 30) * 1e9),
            evidence_refs=[],
            offer={"summary": "Current budget detail", "quotes": [],
                   "uncertainty": "low", "needs_reentry": False},
            confidence=.5, rejected_quotes=0, model_revision="test",
            query_packet_id=query["packet_id"],
            broadcast_packet_id=(broadcast_id if broadcast_id is not None else broadcast["packet_id"]),
            context_source_refs=[], enlightened_source_refs=[],
        )
        self.s.add_packet("OfferPacket", offer)
        selected = focal.item(
            "B1_DETAIL", offer["packet_id"], [event_ref],
            "Current budget detail", self.e["event_id"],
            uncertainty=.1, salience=0., goal=.5, utility=.5, sq=1., cost=.05,
        )
        selected["priority"] = 1.
        return selected

    def _latest_selection(self):
        row = self.s.one(
            "SELECT payload FROM packets WHERE kind='ActionSelection' AND event_id=? ORDER BY rowid DESC LIMIT 1",
            (self.e["event_id"],),
        )
        return json.loads(row["payload"])

    def test_current_jef_broadcast_sources_survive_without_body_offer(self):
        memory_ref = self.s.source("Remembered executive fact", "MEMORY")
        broadcast, refs = self._broadcast(memory_ref)
        focal.ActionGate(self.s).select(
            self.e, route="simple", direct=False,
            resource_state="NORMAL", coalition=[],
        )
        selection = self._latest_selection()
        validate("ActionSelection", selection)
        self.assertEqual(selection["provenance"], refs)
        from v13.world_jepa_store_authority import _selection_source_refs
        consumed = _selection_source_refs(
            self.s, self.e["event_id"], self.e["brain_generation_id"], self.e["source_ref"]
        )
        key = (memory_ref["source_id"], memory_ref["sha256"],
               memory_ref["char_start"], memory_ref["char_end"], memory_ref["modality"])
        self.assertIn(key, consumed)

    def test_selected_body_offer_includes_the_exact_broadcast_sources(self):
        memory_ref = self.s.source("Executive memory source", "MEMORY")
        broadcast, refs = self._broadcast(memory_ref, version=9)
        selected = self._offer(broadcast)
        focal.ActionGate(self.s).select(
            self.e, route="detail", direct=False,
            resource_state="NORMAL", coalition=[selected],
        )
        self.assertEqual(self._latest_selection()["provenance"], refs)

    def test_offer_query_broadcast_mismatch_fails_before_action_selection(self):
        memory_ref = self.s.source("Executive memory source", "MEMORY")
        broadcast, _ = self._broadcast(memory_ref, version=11)
        selected = self._offer(broadcast, broadcast_id="wrong-broadcast-id")
        before = self.s.one(
            "SELECT COUNT(*) AS n FROM packets WHERE kind='ActionSelection' AND event_id=?",
            (self.e["event_id"],),
        )["n"]
        with self.assertRaisesRegex(ValueError, "query binding"):
            focal.ActionGate(self.s).select(
                self.e, route="detail", direct=False,
                resource_state="NORMAL", coalition=[selected],
            )
        after = self.s.one(
            "SELECT COUNT(*) AS n FROM packets WHERE kind='ActionSelection' AND event_id=?",
            (self.e["event_id"],),
        )["n"]
        self.assertEqual(after, before)
