"""Run520: source-only native B2 raw quote -> source-verified quote ancestry."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from tests.test_run513_b2_receipt_postflight import make_stage, update_rows
import run513_b2_receipt_postflight as postflight


class Run520QuoteLineage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.rows, _ = make_stage(self.work)

    def audit(self):
        update_rows(self.work, self.rows)
        return postflight.audit(self.work, 0)

    def test_original_synthetic_stage_still_passes(self):
        report, rows = self.audit()
        self.assertEqual(report["source_bound_rows"], 12)
        self.assertEqual(len(rows), 12)
        self.assertFalse(report["native_execution_independently_confirmed"])

    def test_source_exact_forged_quote_without_native_candidate_rejected(self):
        row = self.rows[0]
        # Existing source/ref/offset guard alone accepts this tampering.
        row["raw_offer_quotes"] = ["a quote never present in the source"]
        slots = postflight.check_slots(row, {
            "history": [x["source_text"] for x in row["source_slots"][:3]],
            "current": row["source_slots"][3]["source_text"],
        })
        postflight.check_quotes(row, slots)
        with self.assertRaisesRegex(ValueError, "ACCEPTED_QUOTE_NOT_IN_NATIVE_OFFER"):
            self.audit()

    def test_pointer_widening_keeps_raw_quote_ancestry(self):
        row = self.rows[0]
        original = row["source_slots"][0]["source_text"]
        widened = original[:min(80, len(original))]
        self.assertGreater(len(widened), len(row["raw_offer_quotes"][0]))
        row["quotes"][0]["text"] = widened
        row["evidence_refs"][0]["char_end"] = len(widened)
        self.audit()

    def test_casefold_and_whitespace_normalization(self):
        row = self.rows[0]
        row["raw_offer_quotes"] = [" ".join(row["quotes"][0]["text"].upper().split())]
        self.audit()

    def test_duplicate_raw_candidate_can_collapse_to_one_evidence_ref(self):
        row = self.rows[0]
        row["raw_offer_quotes"].append(row["raw_offer_quotes"][0])
        self.audit()

    def test_too_many_accepted_refs_for_native_candidates(self):
        row = self.rows[0]
        row["quotes"].append(copy.deepcopy(row["quotes"][0]))
        row["evidence_refs"].append(copy.deepcopy(row["evidence_refs"][0]))
        with self.assertRaisesRegex(ValueError, "ACCEPTED_QUOTES_EXCEED_NATIVE_CANDIDATES"):
            self.audit()

    def test_rejected_count_limits_accepted_candidate_capacity(self):
        self.rows[0]["rejected_quotes"] = 1
        with self.assertRaisesRegex(ValueError, "ACCEPTED_QUOTES_EXCEED_NATIVE_CANDIDATES"):
            self.audit()

    def test_nonstring_raw_candidate_rejected(self):
        self.rows[0]["raw_offer_quotes"] = [17]
        with self.assertRaisesRegex(ValueError, "RAW_QUOTE_LINEAGE_SCHEMA_DRIFT"):
            self.audit()

    def test_no_raw_quote_and_no_accepted_ref_passes(self):
        row = self.rows[0]
        row["raw_offer_quotes"] = []
        row["quotes"] = []
        row["evidence_refs"] = []
        row["rejected_quotes"] = 0
        self.audit()

    def test_raw_empty_string_cannot_support_accepted_quote(self):
        self.rows[0]["raw_offer_quotes"] = [""]
        with self.assertRaisesRegex(ValueError, "ACCEPTED_QUOTE_NOT_IN_NATIVE_OFFER"):
            self.audit()

    def test_repeated_accepted_quote_needs_distinct_raw_candidates(self):
        row = self.rows[0]
        row["raw_offer_quotes"] = [row["raw_offer_quotes"][0], row["raw_offer_quotes"][0]]
        row["quotes"].append(copy.deepcopy(row["quotes"][0]))
        row["evidence_refs"].append(copy.deepcopy(row["evidence_refs"][0]))
        self.audit()

    def test_raw_quote_list_is_bounded(self):
        row = self.rows[0]
        row["raw_offer_quotes"] = [row["raw_offer_quotes"][0]] * 4
        with self.assertRaisesRegex(ValueError, "RAW_QUOTE_LINEAGE_SCHEMA_DRIFT"):
            self.audit()


if __name__ == "__main__":
    unittest.main()
