"""Run40 original ZIP audit and corruption controls (requires pinned original ZIP)."""
import hashlib
import io
import json
import os
from pathlib import Path
import unittest
import zipfile

from run40_audit_run39_red import (
    ORIGINAL_SHA256, audit_bytes, binding_w7_support, original_w1_w6,
)


class Run40OriginalAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p = os.environ.get("RUN39_ORIGINAL_ZIP")
        if not p or not Path(p).is_file():
            raise unittest.SkipTest("RUN39_ORIGINAL_ZIP not supplied; no original artifact")
        cls.raw = Path(p).read_bytes()
        assert hashlib.sha256(cls.raw).hexdigest() == ORIGINAL_SHA256

    def rewrite(self, changed, update_manifest=False):
        with zipfile.ZipFile(io.BytesIO(self.raw)) as z:
            contents = {n: z.read(n) for n in z.namelist()}
        contents.update(changed)
        if update_manifest:
            contents["SHA256SUMS"] = "".join(
                f"{hashlib.sha256(v).hexdigest()}  ./{k}\n"
                for k, v in sorted(contents.items()) if k != "SHA256SUMS"
            ).encode()
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for k, v in contents.items():
                z.writestr(k, v)
        return out.getvalue()

    def test_original_red_and_nine_rows_verified(self):
        r = audit_bytes(self.raw)
        self.assertEqual(r["original_status"], "RED")
        self.assertEqual(r["manifest_entries"], 84)
        self.assertEqual(r["raw_per_seed_results"], 9)
        self.assertEqual(r["binding_w7"], "UNSCORABLE_SUPPORT_FAIL")
        self.assertEqual(r["w1_w6"]["balanced_slot"]["W4_confidence_tracks_error"], False)
        self.assertFalse(r["w1_w6"]["balanced_slot"]["W6_no_action_attribution_worse"])
        self.assertEqual(r["descriptive_only_due_to_red"]["balanced"]["mean"], -.0043)
        self.assertEqual(r["exploratory_h1"], "NOT_MET_DESCRIPTIVE_ONLY")
        self.assertEqual(r["negative_gates"]["step2"], "UTILITY_FAIL")

    def test_outer_zip_tamper_rejected(self):
        tampered = bytearray(self.raw)
        tampered[-8] ^= 1
        with self.assertRaisesRegex(ValueError, "ORIGINAL_SHA256"):
            audit_bytes(bytes(tampered))

    def test_inner_manifest_tamper_rejected_even_with_rehashed_outer(self):
        tampered = self.rewrite({"TEST_EXIT.txt": b"1\n"})
        with self.assertRaisesRegex(ValueError, "MANIFEST_HASH"):
            audit_bytes(tampered, expected_sha=hashlib.sha256(tampered).hexdigest())

    def test_stage_tamper_rejected_after_rehashing_manifest(self):
        tampered = self.rewrite({"TEST_EXIT.txt": b"1\n"}, update_manifest=True)
        with self.assertRaisesRegex(ValueError, "STAGE_TEST"):
            audit_bytes(tampered, expected_sha=hashlib.sha256(tampered).hexdigest())

    def test_negative_gate_tamper_rejected_after_rehashing_manifest(self):
        with zipfile.ZipFile(io.BytesIO(self.raw)) as z:
            result = json.loads(z.read("RESULT.json"))
        result["step2"] = "UTILITY_PASS"
        tampered = self.rewrite({"RESULT.json": json.dumps(result).encode()}, update_manifest=True)
        with self.assertRaisesRegex(ValueError, "NEGATIVE_GATES"):
            audit_bytes(tampered, expected_sha=hashlib.sha256(tampered).hexdigest())

    def test_support_minimum_not_silently_relaxed(self):
        with zipfile.ZipFile(io.BytesIO(self.raw)) as z:
            row = json.loads(z.read("work/balanced_slot-501-RESULT.json"))
        self.assertEqual(row["attribution"]["jepa"]["n"]["world_only"], 14)
        self.assertFalse(binding_w7_support([row]))
        row["attribution"]["jepa"]["n"]["world_only"] = 15
        row["attribution"]["no_action"]["n"]["world_only"] = 15
        self.assertTrue(binding_w7_support([row]))

    def test_independent_gate_readout_does_not_promote(self):
        with zipfile.ZipFile(io.BytesIO(self.raw)) as z:
            rows = [json.loads(z.read(f"work/balanced_slot-{seed}-RESULT.json"))
                    for seed in (501, 502, 503)]
        gates, summary = original_w1_w6(rows)
        self.assertTrue(gates["W1_cf_retrieval_covered"])
        self.assertFalse(gates["W4_confidence_tracks_error"])
        self.assertFalse(gates["W6_no_action_attribution_worse"])
        self.assertLess(summary["rho"], 0)


if __name__ == "__main__":
    unittest.main()