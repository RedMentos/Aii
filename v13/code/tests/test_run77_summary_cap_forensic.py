"""Read-only original Run77 compact forensic and deliberate tamper controls."""
import io
import json
import os
from pathlib import Path
import sys
import unittest
from zipfile import ZipFile, ZIP_DEFLATED

try:
    from scripts import run77_summary_cap_forensic as a
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import run77_summary_cap_forensic as a

ORIGINAL = Path(os.environ.get("V13_RUN77_COMPACT_ZIP", "/mnt/data/run77_forensic_compact_41187084497.zip"))


def mutate(raw, replace=None, remove=(), manifest=None):
    with ZipFile(io.BytesIO(raw)) as z:
        contents = {name: z.read(name) for name in z.namelist() if name not in remove}
    contents.update(replace or {})
    if manifest is None:
        contents["SHA256SUMS"] = "".join(
            a.sha(data) + "  ./" + name + "\n"
            for name, data in sorted(contents.items())
            if name not in a.LATE_UNHASHED | {"SHA256SUMS"}).encode()
    else:
        contents["SHA256SUMS"] = manifest
    out = io.BytesIO()
    with ZipFile(out, "w", compression=ZIP_DEFLATED) as z:
        for name, data in contents.items():
            z.writestr(name, data)
    return out.getvalue()


def edit_report(raw, edit):
    with ZipFile(io.BytesIO(raw)) as z:
        report = json.loads(z.read("report.json"))
    edit(report)
    return mutate(raw, replace={"report.json": json.dumps(report, separators=(",", ":")).encode()})


@unittest.skipUnless(ORIGINAL.is_file(), "Run77 original compact ZIP unavailable")
class Run77SummaryCapForensicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = ORIGINAL.read_bytes()

    def check_red(self, raw, code):
        with self.assertRaisesRegex(a.AuditError, code):
            a.audit_bytes(raw, expected_zip_sha=a.sha(raw))

    def test_01_original_retains_scientific_and_verifier_red(self):
        result = a.audit_bytes(self.original)
        self.assertEqual(result["status"], "CAP_CONFOUND_OBSERVED_NOT_CAUSAL_PROOF")
        self.assertEqual(result["persisted_summary_lengths"], {"48": 36})
        self.assertEqual(result["original_independent_verifier"], "RED")
        self.assertEqual(result["original_inner_hashed"], 55)
        self.assertFalse(result["step2_promoted"])
        self.assertFalse(result["causal_summary_cap_proven"])

    def test_02_exact_schema_budget_math(self):
        self.assertEqual(a.summary_cap(96, 80), 48)
        self.assertEqual(a.summary_cap(160, 80), 84)
        self.assertEqual(a.summary_cap(96, 0), 65)
        self.assertGreater(a.summary_cap(256, 80), 84)

    def test_03_outer_sha_tamper(self):
        with self.assertRaisesRegex(a.AuditError, "ZIP_SHA_RED"):
            a.audit_bytes(self.original + b"tamper")

    def test_04_inner_hash_tamper(self):
        with ZipFile(io.BytesIO(self.original)) as z:
            manifest = z.read("SHA256SUMS")
        self.check_red(mutate(self.original, replace={"NATIVE_RAW.log": b"tamper"},
                              manifest=manifest), "MEMBER_SHA_RED")

    def test_05_missing_offer(self):
        def edit(r):
            r["rows"][0]["offers"].pop()
        self.check_red(edit_report(self.original, edit), "OFFER_COUNT_RED")

    def test_06_summary_length_forgery(self):
        def edit(r):
            r["rows"][0]["offers"][0]["offer"]["offer"]["summary"] = "A" * 47
        self.check_red(edit_report(self.original, edit), "SUMMARY_LENGTH_NOT_FROZEN_48_RED")

    def test_07_missing_row(self):
        self.check_red(edit_report(self.original, lambda r: r["rows"].pop()), "ROW_COUNT_RED")

    def test_08_scientific_score_forgery(self):
        def edit(r):
            r["scores"]["B1_DETAIL"]["WITH_PRIOR"] = 1
        self.check_red(edit_report(self.original, edit), "FROZEN_NATIVE_REPORT_RED")

    def test_09_original_verifier_failure_cannot_be_rewritten(self):
        self.check_red(mutate(self.original, replace={"VERIFY_EXIT.txt": b"0\n"}),
                       "ORIGINAL_VERIFIER_MUST_STAY_RED")

    def test_10_native_stage_nonzero(self):
        self.check_red(mutate(self.original, replace={"NATIVE_EXIT.txt": b"1\n"}),
                       "STAGE_EXIT_RED:NATIVE")

    def test_11_negative_gate_promotion_refused(self):
        self.check_red(edit_report(self.original, lambda r: r.update(step2="PASS")),
                       "NEGATIVE_GATES_RED")

    def test_12_native_model_forgery(self):
        def edit(r):
            r["rows"][0]["offers"][0]["offer"]["native_metrics"]["actual_model"] = "fake.gguf"
        self.check_red(edit_report(self.original, edit), "NATIVE_OFFER_RED")

    def test_13_driver_b2_evidence_forgery(self):
        def edit(r):
            r["b2_prior_evidence"] = 6
        self.check_red(edit_report(self.original, edit), "FROZEN_NATIVE_REPORT_RED")

    def test_14_missing_late_unhashed_receipt_is_rejected(self):
        self.check_red(mutate(self.original, remove=("SIZE_RAW.log",)), "ZIP_MEMBERS_RED")

    def test_15_diag_original_verifier_error_forgery(self):
        with ZipFile(io.BytesIO(self.original)) as z:
            d = json.loads(z.read("DIAG.json"))
        d["original_error"] = "NO_ERROR"
        self.check_red(mutate(self.original, replace={"DIAG.json": json.dumps(d).encode()}),
                       "ORIGINAL_VERIFIER_DIAGNOSTIC_RED")

if __name__ == "__main__":
    unittest.main()
