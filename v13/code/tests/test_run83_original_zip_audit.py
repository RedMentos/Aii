"""Independent adversarial ZIP reparse. Requires original public Run83 Actions ZIP."""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
import sys
import unittest
import warnings
from zipfile import ZipFile, ZIP_DEFLATED

try:
    from scripts import run83_original_zip_audit as a
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import run83_original_zip_audit as a

ORIGINAL = Path(os.environ.get("V13_RUN83_ORIGINAL_ZIP", "/mnt/data/run83_native_41189536088.zip"))


def mutate(original: bytes, *, replace=None, remove=(), extra=None,
           duplicate=None, manifest=None):
    replace = replace or {}
    extra = extra or {}
    with ZipFile(io.BytesIO(original)) as z:
        contents = {name: z.read(name) for name in z.namelist() if name not in remove}
    contents.update(replace)
    contents.update(extra)
    if manifest is None:
        contents["SHA256SUMS"] = "".join(
            a.sha(data) + "  ./" + name + "\n"
            for name, data in sorted(contents.items()) if name != "SHA256SUMS").encode()
    else:
        contents["SHA256SUMS"] = manifest
    out = io.BytesIO()
    with ZipFile(out, "w", compression=ZIP_DEFLATED) as z:
        for name, data in contents.items():
            z.writestr(name, data)
        if duplicate is not None:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                z.writestr(duplicate, contents[duplicate])
    return out.getvalue()


def edit_report(original, edit):
    with ZipFile(io.BytesIO(original)) as z:
        report = json.loads(z.read("pilot/report.json"))
    edit(report)
    return mutate(original, replace={"pilot/report.json": json.dumps(report, separators=(",", ":")).encode()})


@unittest.skipUnless(ORIGINAL.is_file(), "original public Run83 ZIP unavailable")
class Run83OriginalZipAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = ORIGINAL.read_bytes()

    def check_red(self, raw, code):
        with self.assertRaisesRegex(a.AuditError, code):
            a.audit_bytes(raw, expected_zip_sha=a.sha(raw))

    def test_01_original_all_23_inner_entries_and_10_exits(self):
        result = a.audit_bytes(self.original)
        self.assertEqual(result["inner_files_hashed"], 23)
        self.assertEqual(result["stage_exits_zero"], 10)
        self.assertEqual(result["scores"], {"TYPED_ONLY": 6, "DUAL_SOURCE": 6})
        self.assertTrue(result["synthetic_body_only"])
        self.assertFalse(result["step2_promoted"])

    def test_02_original_digest_is_required(self):
        self.assertEqual(a.sha(self.original), a.ORIGINAL_ZIP_SHA256)
        with self.assertRaisesRegex(a.AuditError, "ORIGINAL_ZIP_SHA_RED"):
            a.audit_bytes(self.original[:-1] + b"x")

    def test_03_member_hash_mismatch(self):
        with ZipFile(io.BytesIO(self.original)) as z:
            manifest = z.read("SHA256SUMS")
        self.check_red(mutate(self.original, replace={"HEAD.txt": b"fake\n"}, manifest=manifest), "MEMBER_SHA_RED")

    def test_04_manifest_missing_member(self):
        with ZipFile(io.BytesIO(self.original)) as z:
            lines = z.read("SHA256SUMS").splitlines(keepends=True)
        self.check_red(mutate(self.original, manifest=b"".join(lines[:-1])), "MANIFEST_COVERAGE_RED")

    def test_05_manifest_duplicate_member(self):
        with ZipFile(io.BytesIO(self.original)) as z:
            m = z.read("SHA256SUMS")
        self.check_red(mutate(self.original, manifest=m + m.splitlines(keepends=True)[0]), "MANIFEST_DUPLICATE_RED")

    def test_06_manifest_invalid_digest(self):
        with ZipFile(io.BytesIO(self.original)) as z:
            m = z.read("SHA256SUMS")
        self.check_red(mutate(self.original, manifest=b"z" + m[1:]), "MANIFEST_SYNTAX_RED")

    def test_07_duplicate_zip_filename(self):
        self.check_red(mutate(self.original, duplicate="HEAD.txt"), "DUPLICATE_ZIP_MEMBER_RED")

    def test_08_extra_zip_member(self):
        self.check_red(mutate(self.original, extra={"hidden.log": b"secret"}), "ZIP_MEMBERS_RED")

    def test_09_missing_zip_member(self):
        self.check_red(mutate(self.original, remove=("NATIVE_RAW.log",)), "ZIP_MEMBERS_RED")

    def test_10_wrong_head_even_if_rehashed(self):
        self.check_red(mutate(self.original, replace={"HEAD.txt": b"0" * 40 + b"\n"}), "HEAD_RED")

    def test_11_wrong_git_pin_even_if_rehashed(self):
        with ZipFile(io.BytesIO(self.original)) as z:
            p = z.read("PINS.txt").decode()
        self.check_red(mutate(self.original, replace={"PINS.txt": p.replace("218464b1", "118464b1").encode()}), "PIN_BLOB_RED")

    def test_12_nonzero_native_exit_even_if_rehashed(self):
        self.check_red(mutate(self.original, replace={"NATIVE_EXIT.txt": b"1\n"}), "STAGE_EXIT_RED:NATIVE")

    def test_13_nonzero_privacy_exit_even_if_rehashed(self):
        self.check_red(mutate(self.original, replace={"PRIVACY_EXIT.txt": b"1\n"}), "STAGE_EXIT_RED:PRIVACY")

    def test_14_forged_native_body_claim(self):
        self.check_red(edit_report(self.original, lambda r: r.update(body_native_call_count=12)), "REPORT_PIN_OR_AUTHORITY_RED")

    def test_15_missing_native_case(self):
        self.check_red(edit_report(self.original, lambda r: r["cases"].pop()), "CASE_COUNT_RED")

    def test_16_wrong_arm_order(self):
        def edit(r):
            r["cases"][0], r["cases"][1] = r["cases"][1], r["cases"][0]
        self.check_red(edit_report(self.original, edit), "CASE_ORDER_OR_ORACLE_RED")

    def test_17_output_forgery_with_updated_output_hash(self):
        def edit(r):
            c = r["cases"][0]
            c["output"] = '{"action":"B"}'
            c["output_sha256"] = a.sha(c["output"].encode())
            c["output_bytes"] = len(c["output"].encode())
        self.check_red(edit_report(self.original, edit), "OUTPUT_SCHEMA_OR_SCORE_RED")

    def test_18_extra_output_key_with_updated_hash(self):
        def edit(r):
            c = r["cases"][0]
            c["output"] = '{"action":"A","tool":"execute"}'
            c["output_sha256"] = a.sha(c["output"].encode())
            c["output_bytes"] = len(c["output"].encode())
        self.check_red(edit_report(self.original, edit), "OUTPUT_SCHEMA_OR_SCORE_RED")

    def test_19_duplicate_json_output_key(self):
        def edit(r):
            c = r["cases"][0]
            c["output"] = '{"action":"A","action":"A"}'
            c["output_sha256"] = a.sha(c["output"].encode())
            c["output_bytes"] = len(c["output"].encode())
        self.check_red(edit_report(self.original, edit), "OUTPUT_JSON_RED")

    def test_20_dual_body_hypothesis_tamper(self):
        def edit(r):
            c = r["cases"][1]
            p = json.loads(c["input_messages"][1]["content"])
            p["body_observations"][0]["hypothesis"]["summary"] = "No contradiction"
            c["input_messages"][1]["content"] = json.dumps(p, sort_keys=True, separators=(",", ":"))
            c["input_sha256"] = a.sha(json.dumps(c["input_messages"], separators=(",", ":")).encode())
        self.check_red(edit_report(self.original, edit), "DUAL_BODY_HYPOTHESIS_RED")

    def test_21_current_source_sha_forgery(self):
        def edit(r):
            c = r["cases"][1]
            p = json.loads(c["input_messages"][1]["content"])
            p["current_source"]["source_ref"]["sha256"] = "0" * 64
            c["input_messages"][1]["content"] = json.dumps(p, sort_keys=True, separators=(",", ":"))
            c["input_sha256"] = a.sha(json.dumps(c["input_messages"], separators=(",", ":")).encode())
        self.check_red(edit_report(self.original, edit), "CURRENT_SOURCE_HASH_RED")

    def test_22_negative_gate_promotion_refused(self):
        self.check_red(edit_report(self.original, lambda r: r.update(step2="PASS")), "REPORT_PIN_OR_AUTHORITY_RED")

    def test_23_repeated_identical_exit_hashes_not_collapsed(self):
        with ZipFile(io.BytesIO(self.original)) as z:
            rows = z.read("SHA256SUMS").decode().splitlines()
        self.assertEqual(len(rows), 23)
        self.assertEqual(sum("_EXIT.txt" in row for row in rows), 10)
        self.assertEqual(len({row.split("  ")[0] for row in rows if "_EXIT.txt" in row}), 1)
        self.assertEqual(a.audit_bytes(self.original)["inner_files_hashed"], 23)

if __name__ == "__main__":
    unittest.main()
