"""HB1a independent closed-record verifier synthetic controls; no native proof."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts import hb1a_independent_native_verifier as verifier
from scripts import hb1a_two_body_native_pilot as plan
from tests.test_hb1a_native_executor_mock import HB1AOrchestrationSoftware, FakePool


class HB1AIndependentVerifierSoftware(unittest.TestCase):
    def make_record(self, root):
        mock = HB1AOrchestrationSoftware()
        home = mock.setup_home(root)
        FakePool.fail_at = None
        mock.run_with_mocks(home, root / "evidence")
        return root / "evidence"

    def test_closed_synthetic_record_consistent_but_not_native_attested(self):
        with TemporaryDirectory() as tmp:
            root = self.make_record(Path(tmp))
            report = verifier.verify(root)
            self.assertEqual(report["body_rows"], 24)
            self.assertEqual(report["c3_rows"], 30)
            self.assertEqual(report["status"],
                             "CLOSED_RECORD_CONSISTENT_NO_NATIVE_ATTESTATION_NO_GATE")
            self.assertFalse(report["canonical_gate_pass"])
            self.assertFalse(report["redmi_measured"])
            self.assertEqual(report["step2_status"], "UTILITY_FAIL")

    def test_tampered_raw_and_gate_claims_fail_closed(self):
        with TemporaryDirectory() as tmp:
            root = self.make_record(Path(tmp))
            raw_path = root / "RAW.json"
            raw = json.loads(raw_path.read_bytes())
            raw["body_rows"][0]["output"] = "TAMPER"
            raw_path.write_text(json.dumps(raw))
            with self.assertRaisesRegex(ValueError, "HB1A_VERIFY_HASH_RED"):
                verifier.verify(root)
        with TemporaryDirectory() as tmp:
            root = self.make_record(Path(tmp))
            receipt_path = root / "RECEIPT.json"
            receipt = json.loads(receipt_path.read_bytes())
            receipt["canonical_gate_pass"] = True
            receipt_path.write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError, "HB1A_VERIFY_RECEIPT_RED"):
                verifier.verify(root)

    def test_tampered_score_with_rehashed_receipt_rejected(self):
        with TemporaryDirectory() as tmp:
            root = self.make_record(Path(tmp))
            score_path = root / "SCORE.json"
            score = json.loads(score_path.read_bytes())
            score["rows"] = 29
            score_path.write_bytes(plan.canonical(score))
            receipt_path = root / "RECEIPT.json"
            receipt = json.loads(receipt_path.read_bytes())
            receipt["score_sha256"] = plan.sha(score_path.read_bytes())
            receipt_path.write_bytes(plan.canonical(receipt))
            with self.assertRaisesRegex(ValueError, "HB1A_VERIFY_SCORE_DRIFT_RED"):
                verifier.verify(root)

    def test_external_fixture_pin_refused(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "HB1A_VERIFY_EXTERNAL_FIXTURE_RED"):
                verifier.verify(Path(tmp), "0" * 64)


if __name__ == "__main__":
    unittest.main()
