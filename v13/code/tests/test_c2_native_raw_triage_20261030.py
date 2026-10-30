"""Adversarial software tests for read-only native artifact triage (no native proof)."""
import hashlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import c2_native_raw_triage_20261030 as m


class NativeTriageSoftware(unittest.TestCase):
    def test_original_pins_are_distinct_and_negative(self):
        self.assertEqual(set(m.RUNS), {"seed53", "seed59"})
        self.assertNotEqual(m.RUNS["seed53"]["fixture"], m.RUNS["seed59"]["fixture"])
        self.assertEqual(m.RUNS["seed53"]["rows"], 24)
        self.assertEqual(m.RUNS["seed59"]["rows"], 12)
        self.assertEqual(m.RUNS["seed53"]["selected"], 0)
        self.assertEqual(m.RUNS["seed59"]["selected"], 4)

    def test_single_arm_contamination_is_not_valid(self):
        row = {"flags": {"valid_native": False,
                         "body_offer_roles": ["B1_DETAIL", "B2_GIST"],
                         "expected_offer_roles": ["B1_DETAIL"]}}
        raw = {"body_process_releases": [{"role": "B1_DETAIL", "process_reaped": True},
                                          {"role": "B2_GIST", "process_reaped": True}]}
        self.assertEqual(m.diagnose_row(row, raw), "OFFER_OR_RELEASE_ROLE_CONTAMINATION")
        row["flags"]["expected_offer_roles"] = ["B1_DETAIL", "B2_GIST"]
        self.assertEqual(m.diagnose_row(row, raw), "OTHER_INVALID_NATIVE")
        row["flags"]["valid_native"] = True
        self.assertEqual(m.diagnose_row(row, raw), "VALID")

    def test_pre_close_missing_receipt_is_not_process_failure_proof(self):
        row = {"flags": {"valid_native": False, "body_offer_roles": ["B2_GIST"],
                         "expected_offer_roles": ["B2_GIST"]}}
        self.assertEqual(m.diagnose_row(row, {"body_process_releases": []}),
                         "OFFER_WITHOUT_PRE_CLOSE_RELEASE_RECEIPT")
        self.assertEqual(m.diagnose_row(row, {"body_process_releases": [
            {"role": "B2_GIST", "process_reaped": False}]}), "BODY_PROCESS_NOT_REAPED")

    def fixture_zip(self, path, *, wrong_inner=False, extra=False, duplicate=False):
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("report.json", b"{}")
            if extra:
                z.writestr("unlisted.txt", "unexpected")
            if duplicate:
                z.writestr("report.json", b"{}")
            digest = "0" * 64 if wrong_inner else hashlib.sha256(b"{}").hexdigest()
            z.writestr("SHA256SUMS", f"{digest}  ./report.json\n")
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def test_zip_manifest_and_crc_verified(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "e.zip"
            h = self.fixture_zip(p)
            self.assertEqual(m.verify_zip(p, h), 1)
            with self.assertRaisesRegex(ValueError, "ZIP_SHA256_MISMATCH"):
                m.verify_zip(p, "0" * 64)

    def test_corrupt_inner_digest_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "e.zip"
            h = self.fixture_zip(p, wrong_inner=True)
            with self.assertRaisesRegex(ValueError, "INNER_SHA256_MISMATCH"):
                m.verify_zip(p, h)

    def test_unlisted_zip_member_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "e.zip"
            h = self.fixture_zip(p, extra=True)
            with self.assertRaisesRegex(ValueError, "INCOMPLETE_INNER_MANIFEST"):
                m.verify_zip(p, h)

    def test_duplicate_zip_member_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "e.zip"
            h = self.fixture_zip(p, duplicate=True)
            with self.assertRaisesRegex(ValueError, "DUPLICATE_ZIP_MEMBER"):
                m.verify_zip(p, h)


if __name__ == "__main__":
    unittest.main()