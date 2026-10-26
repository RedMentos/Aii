"""Run408 synthetic controls: registered public model duplicates excluded, raw retained."""
import hashlib
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import run408_filtered_stage1 as m


class Run408FilteredTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / "original.zip"
        self.weight = b"public!"
        self.weight_path = ("run401-full/attempts/O_s20/attempt-0001/"
                            "arm_home/models/tiny.gguf")
        self.files = {
            "RUN401_HEAD.txt": (m.stage.SOURCE_HEAD + "\n").encode(),
            "RUN401_POSTFLIGHT.json": b'{"rows_verified":42}',
            "RUN401_DEPS_EXIT.txt": b"0\n",
            "RUN401_BOOTSTRAP_EXIT.txt": b"0\n",
            "RUN401_NATIVE_EXIT.txt": b"0\n",
            "RUN401_AUDIT_EXIT.txt": b"0\n",
            "RUN401_PRIVACY_EXIT.txt": b"0\n",
            "RUN401_NATIVE_RAW.log": b"original raw evidence",
            "run401-full/RUN397_PROGRESS.json": b'{"status":"INCOMPLETE"}',
            self.weight_path: self.weight,
        }
        self.catalog = {"models": {"body": {"files": [
            {"local_name": "tiny.gguf", "size": len(self.weight),
             "sha256": hashlib.sha256(self.weight).hexdigest()}]}}}

    def zip(self, extra=None, omit_sha=None, symlink=None):
        files = dict(self.files)
        files.update(extra or {})
        lines = [hashlib.sha256(v).hexdigest() + "  ./" + k
                 for k, v in sorted(files.items()) if k != omit_sha]
        files["RUN401_SHA256SUMS.txt"] = ("\n".join(lines) + "\n").encode()
        with zipfile.ZipFile(self.archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for name, content in files.items():
                info = zipfile.ZipInfo(name)
                info.compress_type = zipfile.ZIP_DEFLATED
                if name == symlink:
                    info.create_system = 3
                    info.external_attr = (stat.S_IFLNK | 0o777) << 16
                z.writestr(info, content)
        return hashlib.sha256(self.archive.read_bytes()).hexdigest()

    def fake_validator(self, root, small):
        self.assertEqual((root / "RUN397_PROGRESS.json").read_bytes(),
                         self.files["run401-full/RUN397_PROGRESS.json"])
        self.assertFalse((root / "attempts/O_s20/attempt-0001/arm_home/models/tiny.gguf").exists())
        self.assertEqual(small["RUN401_HEAD.txt"].decode().strip(), m.stage.SOURCE_HEAD)
        return {"rows_verified": 42, "completed": ["O_s20"]}

    def check(self, digest, dest=None):
        with mock.patch.object(m, "catalog", return_value=self.catalog), \
             mock.patch.object(m.stage, "_validate_native_tree",
                               side_effect=self.fake_validator) as validator:
            result = m.audit_or_restore(self.archive, digest, dest)
        return result, validator

    def test_registered_weight_stream_verified_but_not_restored(self):
        digest = self.zip()
        dest = self.root / "restored"
        result, validator = self.check(digest, dest)
        self.assertEqual(result["status"], "FILTERED_STAGE1_VERIFIED_NO_PROMOTION")
        self.assertEqual(validator.call_count, 1)
        self.assertEqual(result["original_zip_sha256"], digest)
        self.assertEqual(result["omitted_bytes"], len(self.weight))
        self.assertEqual(result["omitted_registered_models"][0]["path"], self.weight_path)
        self.assertFalse(result["canonical_gate_pass"])
        self.assertFalse(result["redmi_measured"])
        self.assertTrue((dest / "RUN397_PROGRESS.json").is_file())
        self.assertEqual(hashlib.sha256(self.archive.read_bytes()).hexdigest(), digest)

    def test_unknown_model_filename_rejected(self):
        digest = self.zip(extra={"run401-full/attempts/O_s20/attempt-0001/"
                                 "arm_home/models/unknown.gguf": b"x"})
        result, validator = self.check(digest)
        self.assertEqual(validator.call_count, 0)
        self.assertIn("UNKNOWN_MODEL_HOME_FILE", str(result["errors"]))

    def test_changed_model_content_even_with_matching_archive_sha_rejected(self):
        self.files[self.weight_path] = b"tampered"
        digest = self.zip()
        result, validator = self.check(digest)
        self.assertEqual(validator.call_count, 0)
        self.assertIn("REGISTERED_MODEL_SHA_MISMATCH", str(result["errors"]))

    def test_model_outside_original_arm_home_rejected(self):
        digest = self.zip(extra={"run401-full/other/evil.gguf": b"x"})
        result, validator = self.check(digest)
        self.assertEqual(validator.call_count, 0)
        self.assertIn("UNREGISTERED_MODEL_PATH", str(result["errors"]))

    def test_model_in_unregistered_arm_rejected(self):
        digest = self.zip(extra={"run401-full/attempts/P_s20/attempt-0001/"
                                 "arm_home/models/tiny.gguf": self.weight})
        result, validator = self.check(digest)
        self.assertEqual(validator.call_count, 0)
        self.assertIn("UNREGISTERED_MODEL_PATH", str(result["errors"]))

    def test_unhashed_model_member_rejected(self):
        digest = self.zip(omit_sha=self.weight_path)
        result, validator = self.check(digest)
        self.assertEqual(validator.call_count, 0)
        self.assertIn("UNHASHED_OR_MISSING_MEMBER", str(result["errors"]))

    def test_model_symlink_rejected_even_when_catalog_matches(self):
        digest = self.zip(symlink=self.weight_path)
        result, validator = self.check(digest)
        self.assertEqual(validator.call_count, 0)
        self.assertIn("SYMLINK_MEMBER", str(result["errors"]))

    def test_original_archive_sha_mismatch_rejected(self):
        self.zip()
        result, validator = self.check("0" * 64)
        self.assertEqual(validator.call_count, 0)
        self.assertIn("ZIP_SHA_MISMATCH", str(result["errors"]))

    def test_receipt_validator_failure_preserves_original_and_destination_absent(self):
        digest = self.zip()
        dest = self.root / "dest"
        with mock.patch.object(m, "catalog", return_value=self.catalog), \
             mock.patch.object(m.stage, "_validate_native_tree",
                               side_effect=ValueError("FORGED_NATIVE_RECEIPT")):
            result = m.audit_or_restore(self.archive, digest, dest)
        self.assertEqual(result["status"], "FILTERED_STAGE1_RED_PRESERVED")
        self.assertIn("FORGED_NATIVE_RECEIPT", str(result["errors"]))
        self.assertFalse(dest.exists())
        self.assertEqual(hashlib.sha256(self.archive.read_bytes()).hexdigest(), digest)


if __name__ == "__main__":
    unittest.main()
