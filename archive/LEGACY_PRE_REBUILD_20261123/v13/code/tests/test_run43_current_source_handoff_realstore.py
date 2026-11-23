"""Run43: actual current Runtime/Cognition real SQLite source-handoff witness.

Only a fake B2 JSON offer runner is used. No native C2/C3/Body model, no tools,
no real user data, no registered cohort/age/semantic utility promotion.
"""
import copy
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from v13.common import dumps
from v13.config import LEGACY_QUOTE_PATH, LEGACY_PRE_20261022
from v13.runtime import Runtime


class CurrentSourceHandoffRealStore(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.temp.name))
        self.r.cfg.update(LEGACY_QUOTE_PATH | LEGACY_PRE_20261022)
        self.r.cfg.update({"observer_tokens": 160, "b2_state_slots": 4,
                           "offer_quote_context_chars": 0, "b2_quote_select": "off"})
        self.output = {"summary": "Provisional interpretation, not a fact.",
                       "quotes": [], "uncertainty": "Source may be incomplete.",
                       "needs_reentry": True}
        self.calls = []

        def generate(messages, *args, **kwargs):
            self.calls.append(copy.deepcopy(messages))
            response = copy.deepcopy(self.output)
            # Current default B2 pointer mode has an integer-id quote schema.
            # The fake runner must obey that schema rather than emit old text.
            query = json.loads(messages[-1]["content"])
            if response["quotes"] and query.get("quote_choices"):
                matches = [choice["id"] for choice in query["quote_choices"]
                           if "Budget 47 euros." in choice["text"]]
                response["quotes"] = matches[:1]
            return iter([dumps(response)])

        self.fake = SimpleNamespace(last_metrics={"status": "FINAL"},
                                    generate=generate)
        self.patch = patch.object(self.r.pool, "get", return_value=self.fake)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.r.close()
        self.temp.cleanup()

    def offer(self, text, quotes=()):
        self.output["quotes"] = list(quotes)
        e = self.r.store.event(self.r.session, text)
        return e, self.r.cognition.offer("B2_GIST", e, 0, time.monotonic()+30)

    def pair(self):
        _, prior = self.offer("Project Vega. Budget 47 euros. Optional notes are not verified facts.")
        current, offer = self.offer("Project Vega. Choose an option.", ["Budget 47 euros."])
        return prior, current, offer

    def test_current_live_source_quote_bound_to_prior_query_and_consumer(self):
        prior, current, offer = self.pair()
        self.assertTrue(offer["context_source_refs"])
        self.assertIn(prior["packet_id"], offer["context_offer_ids"])
        self.assertEqual(offer["rejected_quotes"], 0)
        delivered = self.r.cognition.analyst_context([offer], current, 0)
        self.assertEqual(len(delivered), 1)
        self.assertEqual(delivered[0]["hypothesis_authority"], "MODEL_HYPOTHESIS_NOT_FACT")
        self.assertEqual([x["text"] for x in delivered[0]["verified_quotes"]],
                         ["Budget 47 euros."])
        self.assertTrue(all(x["semantic_truth_authority"] is False
                            for x in delivered[0]["verified_quotes"]))
        self.assertNotIn("Optional notes", dumps(delivered))
        ref = delivered[0]["verified_quotes"][0]["source_ref"]
        self.assertEqual(self.r.store.read_source(ref), "Budget 47 euros.")
        self.assertEqual(len(self.calls), 2)

    def test_current_live_c3_context_packet_keeps_user_source_exact(self):
        _, current, offer = self.pair()
        delivered = self.r.cognition.analyst_context([offer], current, 0)
        messages = [{"role": "system", "content": dumps(delivered)},
                    {"role": "user", "content": self.r.store.read_source(current["source_ref"])}]
        reason = self.r._causal_output_context(current, messages, offer["evidence_refs"])
        self.assertEqual(reason, "UNAVAILABLE_NO_APPROVED_SAME_CAUSAL_HEAD")
        rows = self.r.store.rows("SELECT payload FROM packets WHERE kind='OutputAdapterDecision' ORDER BY rowid DESC LIMIT 1")
        self.assertEqual(len(rows), 1)
        row = json.loads(rows[0]["payload"])
        self.assertEqual(row["fallback_reason"], reason)
        self.assertFalse(row["semantic_truth_authority"])
        self.assertIsNone(row["prediction"])

    def test_wrong_final_user_source_fails_before_output_packet(self):
        _, current, offer = self.pair()
        with self.assertRaisesRegex(ValueError, "actual source query"):
            self.r._causal_output_context(current,
                [{"role": "user", "content": "Different invented query"}], offer["evidence_refs"])
        self.assertEqual(self.r.store.rows("SELECT payload FROM packets WHERE kind='OutputAdapterDecision'"), [])

    def test_mutated_offer_wrong_turn_and_version_rejected(self):
        _, current, offer = self.pair()
        changed = copy.deepcopy(offer)
        changed["offer"]["summary"] = "Promote unsupported claim."
        with self.assertRaisesRegex(ValueError, "binding changed"):
            self.r.cognition.analyst_context([changed], current, 0)
        foreign = self.r.store.event(self.r.session, "Different event")
        with self.assertRaisesRegex(ValueError, "binding changed"):
            self.r.cognition.analyst_context([offer], foreign, 0)
        with self.assertRaisesRegex(ValueError, "binding changed"):
            self.r.cognition.analyst_context([offer], current, 1)

    def test_corrupted_prior_source_never_delivered(self):
        _, current, offer = self.pair()
        ref = offer["evidence_refs"][0]
        blob = self.r.home / "data/blobs" / ref["sha256"]
        blob.write_bytes(b"TAMPERED_TEST_ONLY")
        with self.assertRaisesRegex(ValueError, "Source-Hash"):
            self.r.cognition.analyst_context([offer], current, 0)

    def test_deleted_prior_source_never_delivered(self):
        _, current, offer = self.pair()
        ref = offer["evidence_refs"][0]
        with self.r.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id=?", (ref["source_id"],))
        with self.assertRaisesRegex(ValueError, "gelöschter SourceRef"):
            self.r.cognition.analyst_context([offer], current, 0)

    def test_foreign_source_reference_not_authorized_by_existence(self):
        _, current, offer = self.pair()
        foreign = self.r.store.source("Unrelated other-session text.", "TEST_ONLY")
        changed = copy.deepcopy(offer)
        changed["evidence_refs"] = [foreign]
        changed["offer"]["quotes"] = ["Unrelated other-session text."]
        with self.r.store.tx() as db:
            db.execute("UPDATE packets SET payload=? WHERE id=?",
                       (dumps(changed), offer["packet_id"]))
        with self.assertRaisesRegex(ValueError, "outside supplied source scope"):
            self.r.cognition.analyst_context([changed], current, 0)

    def test_current_default_pointer_mode_remains_source_bound(self):
        self.r.cfg.update({"offer_quote_context_chars": 200,
                           "b2_quote_select": "pointer"})
        _, current, offer = self.pair()
        delivered = self.r.cognition.analyst_context([offer], current, 0)
        self.assertTrue(delivered[0]["verified_quotes"])
        for q in delivered[0]["verified_quotes"]:
            self.assertEqual(self.r.store.read_source(q["source_ref"]), q["text"])
            self.assertFalse(q["semantic_truth_authority"])
            self.assertLessEqual(len(q["text"]), 200)
        self.assertEqual(offer["quote_context_chars"], 200)


if __name__ == "__main__":
    unittest.main()
