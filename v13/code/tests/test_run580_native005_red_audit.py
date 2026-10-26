"""Run580 synthetic adversarial tests of immutable native RED artifact audit."""
import hashlib
from pathlib import Path
import tempfile
import unittest
import warnings
import zipfile

from scripts import run580_native005_red_audit as R


def archive(root, native=1, audit=0, extra=None, bad_sha=False, duplicate=False):
    root = Path(root)
    files = {f"RUN568_{flag}_EXIT.txt":
             (str(native if flag == "NATIVE" else audit if flag == "AUDIT" else 0) + "\n").encode()
             for flag in R.FLAGS}
    files["RUN568_NATIVE_RAW.log"] = b"TimeoutError: native request not completed\n"
    files["RUN568_AUDIT_RAW.log"] = b""
    files["RUN568_BOOTSTRAP_RAW.log"] = b""
    files["RUN568_BATCH_PROGRESS.jsonl"] = b'{"state":"STARTED"}\n'
    if extra:
        files.update(extra)
    lines = [f"{R.digest(value)}  ./{name}" for name, value in sorted(files.items())]
    if bad_sha:
        lines[0] = "0" * 64 + lines[0][64:]
    files["RUN568_SHA256SUMS.txt"] = ("\n".join(lines) + "\n").encode()
    path = root / "original.zip"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for name, value in files.items():
                z.writestr(name, value)
            if duplicate:
                z.writestr("RUN568_NATIVE_EXIT.txt", b"1\n")
    return path, R.digest(path.read_bytes())


class Run580OriginalRed(unittest.TestCase):
    def test_original_nonzero_is_truthful_red_not_native_success(self):
        with tempfile.TemporaryDirectory() as temp:
            path, sha = archive(temp)
            result = R.audit(path, sha)
            self.assertEqual(result["status"], "ORIGINAL_NATIVE_RED_CONFIRMED")
            self.assertEqual(result["nonzero_stages"], ["NATIVE"])
            self.assertEqual(result["original_member_sha256_closed"],
                             result["original_member_count"] - 1)
            self.assertTrue(result["native_attempted"])
            self.assertFalse(result["native_executed_independently_verified"])
            self.assertFalse(result["canonical_gate_pass"])
            self.assertEqual(result["step2_exit"], "UTILITY_FAIL")

    def test_audit_red_is_not_native_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            path, sha = archive(temp, native=0, audit=1)
            result = R.audit(path, sha)
            self.assertEqual(result["nonzero_stages"], ["AUDIT"])
            self.assertFalse(result["native_executed_independently_verified"])

    def test_all_zero_original_is_not_red(self):
        with tempfile.TemporaryDirectory() as temp:
            path, sha = archive(temp, native=0, audit=0)
            with self.assertRaisesRegex(ValueError, "ORIGINAL_NOT_RED"):
                R.audit(path, sha)
            self.assertEqual(R.audit(path, sha, require_red=False)["status"],
                             "ORIGINAL_ALL_ZERO_NOT_RED")

    def test_outer_sha_change_rejected_before_zip(self):
        with tempfile.TemporaryDirectory() as temp:
            path, sha = archive(temp)
            with self.assertRaisesRegex(ValueError, "ORIGINAL_OUTER_SHA256_CHANGED"):
                R.audit(path, "0" * 64)

    def test_traversal_member_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path, sha = archive(temp, extra={"../RUN568_TRAVERSAL.txt": b"x"})
            with self.assertRaisesRegex(ValueError, "UNSAFE_ORIGINAL_MEMBER"):
                R.audit(path, sha)

    def test_duplicate_member_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path, sha = archive(temp, duplicate=True)
            with self.assertRaisesRegex(ValueError, "DUPLICATE_MEMBER"):
                R.audit(path, sha)

    def test_manifest_digest_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path, sha = archive(temp, bad_sha=True)
            with self.assertRaisesRegex(ValueError, "ORIGINAL_SHA_CLOSURE_CHANGED"):
                R.audit(path, sha)

    def test_missing_manifest_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "missing.zip"
            with zipfile.ZipFile(path, "w") as z:
                z.writestr("RUN568_NATIVE_EXIT.txt", "1\n")
            with self.assertRaisesRegex(ValueError, "ORIGINAL_SHA_MANIFEST_MISSING"):
                R.audit(path, R.digest(path.read_bytes()))


if __name__ == "__main__":
    unittest.main()
