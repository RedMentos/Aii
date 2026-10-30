"""Run13W test-first receipt/output consistency guard; synthetic Store only."""
from __future__ import annotations

from tests.test_jef_c3_shadow_fallback_run13v import SourceBoundFallback
from v13.agi import jef_c3_shadow_fallback_run13v as mux


class OutputReceiptBinding(SourceBoundFallback):
    def bound(self, output, **overrides):
        receipt = self.receipt()
        receipt.update({
            "native_output_sha256": mux._sha(output),
            "native_output_bytes": len(output.encode("utf-8")),
        })
        receipt.update(overrides)
        return receipt

    def assert_fallback(self, candidate, receipt):
        result = self.select(candidate, receipt)
        self.assert_shadow(result)
        self.assertEqual(result["selected_provenance"],
                         "JEF_VERIFIED_FALLBACK_SHADOW")
        self.assertEqual(result["selected_text"], self.linked["answer"])
        self.assertTrue(result["source_revalidated"])
        self.assertFalse(result["native_receipt_bound"])

    def test_valid_hash_bound_candidate_remains_shadow_only(self):
        answer = self.linked["answer"]
        result = self.select(answer, self.bound(answer))
        self.assert_shadow(result)
        self.assertEqual(result["selected_provenance"],
                         "C3_FACTS_VERIFIED_SHADOW")
        self.assertTrue(result["native_receipt_bound"])

    def test_different_source_fact_valid_text_cannot_reuse_receipt(self):
        answer = self.linked["answer"]
        altered = answer.replace(" leaves ", "  leaves ", 1)
        self.assertNotEqual(altered, answer)
        # Run13M accepts this whitespace variant: the semantic facts match.
        self.assert_fallback(altered, self.bound(answer))

    def test_missing_wrong_or_malformed_output_binding_is_fallback(self):
        answer = self.linked["answer"]
        for receipt in (
            self.receipt(),
            self.bound(answer, native_output_sha256="0" * 64),
            self.bound(answer, native_output_sha256=mux._sha(answer).upper()),
            self.bound(answer, native_output_sha256=True),
            self.bound(answer, native_output_bytes=len(answer.encode("utf-8")) + 1),
            self.bound(answer, native_output_bytes=True),
            self.bound(answer, native_output_bytes=0),
        ):
            with self.subTest(receipt=receipt):
                self.assert_fallback(answer, receipt)

    def test_boolean_native_calls_cannot_claim_one_native_call(self):
        answer = self.linked["answer"]
        self.assert_fallback(answer, self.bound(answer, native_calls=True))

    def test_source_deleted_still_abstains_with_bound_receipt(self):
        answer = self.linked["answer"]
        with self.runtime.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id="
                       "(SELECT source_id FROM events WHERE id=?)",
                       (self.ids[2],))
        result = self.select(answer, self.bound(answer))
        self.assert_shadow(result)
        self.assertIsNone(result["selected_text"])
        self.assertEqual(result["selected_provenance"], "NONE")
