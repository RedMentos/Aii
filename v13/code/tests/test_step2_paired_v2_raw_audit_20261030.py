"""Independent source-only v2 archive verifier adversarial tests."""
import hashlib
import io
import tempfile
import unittest
from pathlib import Path
import zipfile

from scripts.step2_paired_v2_raw_audit_20261030 import (
    audit_zip, need, verify_manifest, _model_and_route_valid, _score,
    ARMS, MODELS)


class NativeV2ArchiveAuditTests(unittest.TestCase):
    def test_good_manifest_and_crc(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "a.zip"
            raw = b"data\n"
            line = hashlib.sha256(raw).hexdigest() + "  ./evidence.txt\n"
            with zipfile.ZipFile(p, "w") as z:
                z.writestr("evidence.txt", raw)
                z.writestr("SHA256SUMS", line)
            with zipfile.ZipFile(p) as z:
                self.assertEqual(verify_manifest(z), 1)

    def test_bad_manifest_fails(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bad.zip"
            with zipfile.ZipFile(p, "w") as z:
                z.writestr("evidence.txt", b"tampered")
                z.writestr("SHA256SUMS", "0" * 64 + "  ./evidence.txt\n")
            with zipfile.ZipFile(p) as z:
                with self.assertRaisesRegex(ValueError, "INNER_SHA_RED"):
                    verify_manifest(z)

    def test_nonoriginal_sha_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "not-original.zip"
            p.write_bytes(b"not an original artifact")
            with self.assertRaisesRegex(ValueError, "ORIGINAL_ZIP_SHA_RED"):
                audit_zip(p, "0" * 64)

    def test_native_model_and_route_require_all_evidence(self):
        row = {"arm": ARMS[0], "runner_role": "C3_LANGUAGE",
               "native_process_releases": []}
        event = {"checks": {str(i): True for i in range(13)},
                 "source_errors": [], "offers": [],
                 "output_metadata": {
                     "model_generated": True,
                     "route": {"source": "OPERATOR_ROUTE_OVERRIDE"},
                     "c2_packet": {"route": "simple"},
                     "runner": {"role": "C3_LANGUAGE",
                                "actual_model": MODELS[ARMS[0]]}}}
        self.assertTrue(_model_and_route_valid(event, row))
        for mutation in ({"model_generated": False},
                         {"c2_packet": {"route": "both"}},
                         {"runner": {"role": "C3_LANGUAGE",
                                     "actual_model": "foreign.gguf"}}):
            changed = {**event, "output_metadata": {
                **event["output_metadata"], **mutation}}
            self.assertFalse(_model_and_route_valid(changed, row))

    def test_scoring_leaves_and_contradiction(self):
        f = {"project": "Solace", "budget": 167,
             "a": "Opal", "a_cost": 112, "b": "Quartz", "b_cost": 149}
        self.assertEqual(_score(f, "Opal leaves 55 Euro; Quartz leaves 18 Euro.")["correct"], 2)
        self.assertEqual(_score(f, "Opal leaves 55 Euro; Opal has 20 Euro remaining; Quartz leaves 18 Euro.")["correct"], 1)


if __name__ == "__main__":
    unittest.main()
