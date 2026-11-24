"""G15 diagnostic-only original-ZIP full-suite verdict controls."""
from __future__ import annotations

import contextlib
import hashlib
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import warnings
import zipfile

from scripts.g15_fullsuite_diagnostic import REQUIRED_STAGES, compare, main

A = "a" * 40
B = "b" * 40
RED = ("ERROR: test_a (suite.Test)\nFAIL: test_b (suite.Test)\n"
       "Ran 2 tests in 0.1s\nFAILED (failures=1, errors=1)\n")
GREEN = "Ran 2 tests in 0.1s\nOK\n"


def fixture(folder, name, head, raw=RED, full_exit=1, *,
            omit_manifest=False, duplicate=False, stage_red=False):
    files = {
        "HEAD.txt": (head + "\n").encode(),
        "FULL_RAW.log": raw.encode(),
        "FULL_EXIT.txt": (str(full_exit) + "\n").encode(),
    }
    for stage in REQUIRED_STAGES:
        files[stage + "_EXIT.txt"] = (("1" if stage == "CANON" and stage_red
                                       else "0") + "\n").encode()
    if not omit_manifest:
        files["SHA256SUMS"] = "".join(
            hashlib.sha256(content).hexdigest() + "  " + name + "\n"
            for name, content in sorted(files.items())).encode()
    path = Path(folder) / name
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as z:
        for entry, content in files.items():
            z.writestr(entry, content)
        if duplicate:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                z.writestr("FULL_EXIT.txt", files["FULL_EXIT.txt"])
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


class G15VerdictTests(unittest.TestCase):
    def test_historical_red_same_identities_never_promotes(self):
        with TemporaryDirectory() as td:
            a, ha = fixture(td, "a.zip", A)
            b, hb = fixture(td, "b.zip", B)
            result = compare(a, b, ha, hb, A, B)
            self.assertEqual(result["status"], "HISTORICAL_RED_SAME_IDENTITIES")
            self.assertTrue(result["evidence_valid"])
            self.assertFalse(result["software_suite_gate_pass"])
            self.assertEqual(result["candidate"]["identity_count"], 2)
            self.assertEqual(result["added_failure_identities"], [])
            self.assertEqual(result["removed_failure_identities"], [])
            self.assertEqual(result["step2_status"], "UTILITY_FAIL")
            self.assertEqual(result["jepa_weight"], 0)

    def test_new_and_removed_identity_multisets_are_not_waived(self):
        with TemporaryDirectory() as td:
            a, ha = fixture(td, "a.zip", A)
            changed = ("ERROR: test_a (suite.Test)\n"
                       "ERROR: test_c (suite.Test)\n"
                       "Ran 2 tests in 0.1s\nFAILED (errors=2)\n")
            b, hb = fixture(td, "b.zip", B, changed)
            result = compare(a, b, ha, hb, A, B)
            self.assertEqual(result["status"], "RED_CHANGED_IDENTITIES")
            self.assertEqual(result["added_failure_identities"][0]["identity"],
                             "test_c (suite.Test)")
            self.assertEqual(result["removed_failure_identities"][0]["identity"],
                             "test_b (suite.Test)")
            self.assertFalse(result["software_suite_gate_pass"])

    def test_clean_suite_only_passes_with_empty_identity_multiset(self):
        with TemporaryDirectory() as td:
            a, ha = fixture(td, "a.zip", A)
            b, hb = fixture(td, "b.zip", B, GREEN, full_exit=0)
            result = compare(a, b, ha, hb, A, B)
            self.assertEqual(result["status"], "FULL_PASS")
            self.assertTrue(result["software_suite_gate_pass"])
            self.assertFalse(result["canonical_architecture_complete"])
            self.assertFalse(result["redmi_measured"])

    def test_false_green_exit_is_integrity_red(self):
        with TemporaryDirectory() as td:
            a, ha = fixture(td, "a.zip", A)
            b, hb = fixture(td, "b.zip", B, RED, full_exit=0)
            result = compare(a, b, ha, hb, A, B)
            self.assertEqual(result["status"], "INTEGRITY_RED")
            self.assertFalse(result["evidence_valid"])

    def test_wrong_outer_hash_or_head_is_integrity_red(self):
        with TemporaryDirectory() as td:
            a, ha = fixture(td, "a.zip", A)
            b, hb = fixture(td, "b.zip", B)
            for h, head in (("0" * 64, B), (hb, "c" * 40)):
                with self.subTest(h=h, head=head):
                    self.assertEqual(compare(a, b, ha, h, A, head)["status"],
                                     "INTEGRITY_RED")

    def test_missing_manifest_duplicate_name_and_bad_stage_rejected(self):
        with TemporaryDirectory() as td:
            a, ha = fixture(td, "a.zip", A)
            for name, kwargs in (
                ("missing.zip", {"omit_manifest": True}),
                ("duplicate.zip", {"duplicate": True}),
                ("stage.zip", {"stage_red": True}),
            ):
                with self.subTest(name=name):
                    b, hb = fixture(td, name, B, **kwargs)
                    self.assertEqual(compare(a, b, ha, hb, A, B)["status"],
                                     "INTEGRITY_RED")

    def test_crc_corruption_rejected_even_with_matching_outer_hash(self):
        with TemporaryDirectory() as td:
            a, ha = fixture(td, "a.zip", A)
            b, _ = fixture(td, "b.zip", B, RED + "UNIQUE_FAULT_SENTINEL\n")
            data = b.read_bytes()
            self.assertEqual(data.count(b"UNIQUE_FAULT_SENTINEL"), 1)
            b.write_bytes(data.replace(b"UNIQUE_FAULT_SENTINEL",
                                       b"UNIQUE_FAULT_SFNTINEL"))
            hb = hashlib.sha256(b.read_bytes()).hexdigest()
            self.assertEqual(compare(a, b, ha, hb, A, B)["status"],
                             "INTEGRITY_RED")

    def test_cli_exit_is_diagnostic_not_suite_waiver(self):
        with TemporaryDirectory() as td:
            a, ha = fixture(td, "a.zip", A)
            b, hb = fixture(td, "b.zip", B)
            args = ["--baseline", str(a), "--candidate", str(b),
                    "--baseline-sha256", ha, "--candidate-sha256", hb,
                    "--baseline-head", A, "--candidate-head", B]
            with contextlib.redirect_stdout(io.StringIO()) as out:
                code = main(args)
            self.assertEqual(code, 0)
            self.assertIn('"software_suite_gate_pass": false', out.getvalue())
            args[args.index("--candidate-sha256") + 1] = "0" * 64
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(args), 2)


if __name__ == "__main__":
    unittest.main()
