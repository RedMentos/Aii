"""System-wide Enlightened Space: real SQLite, source erasure, scoped organ exchange.

All tests run locally without native-model claims. Native delivery uses the
separate coordinator test, with deterministic role generators.
"""
import json
from pathlib import Path
import tempfile
import time
import unittest

from v13.enlightened_space import EnlightenedSpace, SCHEMA
from v13.runtime import Runtime


class GlobalSpaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.s = self.r.store
        self.space = self.r.space()
        self.e = self.s.event(self.r.session, "The reserve is 120 euros. Keep the budget.")
        self.ref = self.e["source_ref"]

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def later(self, text="How much is the reserve budget?"):
        return self.s.event(self.r.session, text)

    def body_packet(self, producer, event, ref, ident):
        payload = {
            "packet_id": ident, "event_id": event["event_id"],
            "brain_generation_id": event["brain_generation_id"],
            "role": producer, "evidence_refs": [ref],
        }
        # A verified production OfferPacket is enforced by store.add_packet;
        # this isolated test directly seeds the exact persisted row for the
        # separate cross-module packet-binding check.
        with self.s.tx() as tx:
            tx.execute(
                "INSERT INTO packets VALUES (?,?,?,?,?,?)",
                (ident, "OfferPacket", event["event_id"],
                 event["brain_generation_id"], json.dumps(payload), time.time()),
            )

    def test_same_space_shared_across_all_organs_and_both_context_streams(self):
        roles = [
            ("A_PERCEPTION", "EXACT", "SOURCE_POINTER"),
            ("STREAM_A", "SEMANTIC", "SOURCE_POINTER"),
            ("STREAM_B", "EXACT", "SOURCE_POINTER"),
            ("MEMORY", "SEMANTIC", "USER_MEMORY_CUE"),
            ("WORLD", "PREDICTION", "CONTROL_ONLY"),
            ("SELF", "CONTROL", "CONTROL_ONLY"),
            ("JEPA", "FEEDBACK", "MEASURED_DIGITAL_OUTCOME"),
            ("C1_JEF", "CONTROL", "CONTROL_ONLY"),
            ("C2_CONTROL", "CONTROL", "CONTROL_ONLY"),
            ("C4_FOCAL", "FOCAL", "CONTROL_ONLY"),
            ("C5_ACTION", "CONTROL", "CONTROL_ONLY"),
            ("INQUISITION", "CONTROL", "CONTROL_ONLY"),
            ("C3_LANGUAGE", "FEEDBACK", "CONTROL_ONLY"),
            ("OUTCOME", "FEEDBACK", "MEASURED_DIGITAL_OUTCOME"),
        ]
        for role, channel, authority in roles:
            refs = [self.ref] if authority in (
                "SOURCE_POINTER", "USER_MEMORY_CUE") else []
            response = self.space.publish(
                self.e, role, channel, authority=authority,
                summary="Reserve budget cross-organ", source_refs=refs)
            self.assertEqual(response["status"], "PUBLISHED")
        counts = self.space.report(self.e["brain_generation_id"])
        self.assertEqual(counts["schema"], SCHEMA)
        self.assertEqual(counts["entries"], len(roles))
        self.assertFalse(counts["trained_latent"])
        self.assertTrue(all(counts["organ_messages"][r] == 1 for r, _, _ in roles))
        future = self.later()
        shared = self.space.consume(future, "B2_GIST", "reserve budget",
                                    max_messages=5)
        senders = {x["from"] for x in shared["messages"]}
        self.assertTrue({"STREAM_A", "MEMORY"} & senders)
        self.assertTrue(shared["source_refs"])
        self.assertFalse(shared["trained_latent"])

    def test_native_body_hypotheses_are_not_facts_or_unselected_c3_input(self):
        self.body_packet("B1_DETAIL", self.e, self.ref, "pkt_body_test_1")
        self.body_packet("B2_GIST", self.e, self.ref, "pkt_body_test_2")
        for role, ident in [("B1_DETAIL", "pkt_body_test_1"),
                            ("B2_GIST", "pkt_body_test_2")]:
            self.space.publish(self.e, role, "SEMANTIC",
                               summary="Model says reserve is 999 euros",
                               source_refs=[self.ref],
                               authority="MODEL_HYPOTHESIS", packet_id=ident)
        no_selection = self.space.consume(self.e, "C3_LANGUAGE", "reserve")
        self.assertFalse(any(m["from"] in ("B1_DETAIL", "B2_GIST")
                             for m in no_selection["messages"]))
        approved = self.space.consume(self.e, "C3_LANGUAGE", "reserve",
                                      selected_offers=["pkt_body_test_1"],
                                      max_messages=5)
        body = [m for m in approved["messages"]
                if m["from"] in ("B1_DETAIL", "B2_GIST")]
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["from"], "B1_DETAIL")
        self.assertEqual(body[0]["authority"], "MODEL_HYPOTHESIS")
        self.assertIn("999", body[0]["semantic_cue_not_fact"])
        self.assertIn("120", body[0]["exact_sources"][0]["exact_source_text"])

    def test_invalid_role_unbound_offer_and_false_source_are_rejected(self):
        with self.assertRaises(ValueError):
            self.space.publish(self.e, "ANOTHER_CHATBOT", "SEMANTIC",
                               summary="confident")
        with self.assertRaises(ValueError):
            self.space.publish(self.e, "B1_DETAIL", "SEMANTIC",
                               summary="unverified", authority="MODEL_HYPOTHESIS")
        with self.assertRaises(ValueError):
            self.space.publish(self.e, "B1_DETAIL", "SEMANTIC",
                               summary="fake", authority="MODEL_HYPOTHESIS",
                               source_refs=[self.ref], packet_id="pkt_nonexistent")
        other = self.later()
        self.body_packet("B2_GIST", other, self.ref, "pkt_other_event")
        with self.assertRaises(ValueError):
            self.space.publish(self.e, "B2_GIST", "SEMANTIC",
                               summary="cross event", authority="MODEL_HYPOTHESIS",
                               source_refs=[self.ref], packet_id="pkt_other_event")

    def test_deleted_exact_source_disables_all_dependent_shared_content(self):
        self.space.publish(self.e,"MEMORY","SEMANTIC",
                           summary="reserve budget",source_refs=[self.ref],
                           authority="USER_MEMORY_CUE")
        self.assertEqual(len(self.space.consume(self.later(), "C3_LANGUAGE",
                                                "reserve")["messages"]), 1)
        with self.s.tx() as tx:
            tx.execute("UPDATE sources SET deleted=1 WHERE id=?",
                       (self.ref["source_id"],))
        self.assertEqual(self.space.consume(self.later(), "C3_LANGUAGE",
                                            "reserve")["messages"], [])

    def test_recurring_semantics_extend_timescale_without_erasing_exact_sources(self):
        self.space.publish(self.e, "MEMORY", "SEMANTIC",
                           summary="reserve budget important",
                           authority="USER_MEMORY_CUE", source_refs=[self.ref])
        other=self.later()
        self.space.publish(other, "MEMORY", "SEMANTIC",
                           summary="reserve budget important",
                           authority="USER_MEMORY_CUE", source_refs=[self.ref])
        report=self.space.report(self.e["brain_generation_id"])
        self.assertGreaterEqual(report["timescales"]["MEDIUM"],1)
        self.assertEqual(report["entries"],2)

    def test_exact_input_not_repeated_in_same_turn_and_no_cross_generation_leak(self):
        self.space.publish(self.e,"A_PERCEPTION","EXACT",
                           summary="reserve current",authority="SOURCE_POINTER",
                           source_refs=[self.ref])
        self.space.publish(self.e,"STREAM_A","SEMANTIC",
                           summary="reserve current",authority="SOURCE_POINTER",
                           source_refs=[self.ref])
        self.space.publish(self.e,"STREAM_B","EXACT",
                           summary="reserve current",authority="SOURCE_POINTER",
                           source_refs=[self.ref])
        self.assertFalse(self.space.consume(self.e,"B1_DETAIL","reserve")["messages"])
        changed = dict(self.e, brain_generation_id="gen_future_independent")
        self.assertEqual(self.space.report(changed["brain_generation_id"])["entries"],0)

    def test_output_budgets_and_event_capacity(self):
        for n in range(28):
            result=self.space.publish(self.e, "SELF", "CONTROL",
                                      summary=f"unique state {n}")
            self.assertEqual(result["status"],
                             "PUBLISHED" if n<24 else "EVENT_BUDGET")
        with self.assertRaises(ValueError):
            self.space.consume(self.e,"C3_LANGUAGE","reserve",max_chars=901)
        with self.assertRaises(ValueError):
            self.space.consume(self.e,"C3_LANGUAGE","reserve",max_messages=6)


if __name__ == "__main__":
    unittest.main()
