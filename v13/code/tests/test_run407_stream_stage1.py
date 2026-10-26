"""Run407 source-only adversarial tests; never evidence of real native execution."""
import hashlib
import os
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import run407_stream_stage1 as m


class Run407StreamTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / "stage1.zip"
        self.files = {
            "RUN401_HEAD.txt": (m.stage.SOURCE_HEAD + "\n").encode(),
            "RUN401_POSTFLIGHT.json": b'{"rows_verified":42}',
            "RUN401_DEPS_EXIT.txt": b"0\n",
            "RUN401_BOOTSTRAP_EXIT.txt": b"0\n",
            "RUN401_NATIVE_EXIT.txt": b"0\n",
            "RUN401_AUDIT_EXIT.txt": b"0\n",
            "RUN401_PRIVACY_EXIT.txt": b"0\n",
            "RUN401_INSTALLED_RAW.log": b"RUNNER_VERIFIED " + m.stage.RUN401_EXECUTABLE_SHA256.encode() + b"\n",
            "RUN401_NATIVE_RAW.log": b"native raw stays in ZIP only",
            "run401-full/RUN397_PROGRESS.json": b'{"status":"INCOMPLETE"}',
            "run401-full/attempts/O_s20/attempt-0001/step2_O_s20.json": b'{"fixture":"synthetic"}',
        }

    def make_zip(self, extra=None, manifest_override=None, duplicates=None, symlink=None):
        files = dict(self.files)
        if extra:
            files.update(extra)
        lines = [hashlib.sha256(v).hexdigest() + "  ./" + k
                 for k, v in sorted(files.items())]
        if manifest_override is not None:
            lines = manifest_override
        files["RUN401_SHA256SUMS.txt"] = ("\n".join(lines) + "\n").encode()
        with zipfile.ZipFile(self.archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for name, value in files.items():
                info = zipfile.ZipInfo(name)
                info.compress_type = zipfile.ZIP_DEFLATED
                if name == symlink:
                    info.create_system = 3
                    info.external_attr = (stat.S_IFLNK | 0o777) << 16
                z.writestr(info, value)
            for name, value in duplicates or []:
                z.writestr(name, value)
        return hashlib.sha256(self.archive.read_bytes()).hexdigest()

    def check(self, digest, destination=None):
        with mock.patch.object(m.stage, "_validate_native_tree",
                               side_effect=self.fake_validator) as check:
            report = m.audit_or_restore(self.archive, digest, destination)
        return report, check

    def fake_validator(self, work, small):
        self.assertEqual((work / "RUN397_PROGRESS.json").read_bytes(),
                         self.files["run401-full/RUN397_PROGRESS.json"])
        self.assertEqual(small["RUN401_NATIVE_EXIT.txt"], b"0\n")
        return {"completed": ["O_s20"], "rows_verified": 42, "remaining_arms": 8}

    def test_actual_streaming_all_member_hashes_and_crc_source_only(self):
        digest = self.make_zip()
        report, checked = self.check(digest)
        self.assertEqual(report["status"], "STAGE1_STREAM_VERIFIED_NO_PROMOTION")
        self.assertEqual(report["members_verified"], len(self.files))
        self.assertTrue(report["zip_crc_checked"])
        self.assertTrue(report["all_member_sha_checked"])
        self.assertEqual(report["rows_verified"], 42)
        self.assertFalse(report["canonical_gate_pass"])
        self.assertFalse(report["redmi_measured"])
        self.assertEqual(checked.call_count, 1)

    def test_atomic_restore_is_fresh_only_and_original_zip_unchanged(self):
        digest = self.make_zip()
        dest = self.root / "restored"
        report, _ = self.check(digest, dest)
        self.assertEqual(report["status"], "STAGE1_STREAM_VERIFIED_NO_PROMOTION")
        self.assertEqual((dest / "RUN397_PROGRESS.json").read_bytes(),
                         self.files["run401-full/RUN397_PROGRESS.json"])
        self.assertFalse((dest / "RUN401_NATIVE_RAW.log").exists())
        self.assertEqual(hashlib.sha256(self.archive.read_bytes()).hexdigest(), digest)
        second, checked = self.check(digest, dest)
        self.assertEqual(second["status"], "STAGE1_STREAM_RED_PRESERVED")
        self.assertEqual(checked.call_count, 0)
        self.assertIn("DESTINATION_NOT_FRESH", str(second["errors"]))

    def test_tampered_manifest_fails_closed(self):
        files = dict(self.files)
        lines = ["0" * 64 + "  ./RUN401_HEAD.txt"] + [
            hashlib.sha256(v).hexdigest() + "  ./" + k for k, v in files.items()
            if k != "RUN401_HEAD.txt"]
        digest = self.make_zip(manifest_override=lines)
        report, checked = self.check(digest)
        self.assertEqual(checked.call_count, 0)
        self.assertIn("MEMBER_SHA_MISMATCH", str(report["errors"]))

    def test_wrong_source_head_is_rejected(self):
        self.files["RUN401_HEAD.txt"] = b"forged\n"
        digest = self.make_zip()
        report, checked = self.check(digest)
        self.assertEqual(checked.call_count, 0)
        self.assertIn("STAGE1_SOURCE_HEAD_MISMATCH", str(report["errors"]))

    def test_missing_member_in_manifest_rejected(self):
        lines = [hashlib.sha256(v).hexdigest() + "  ./" + k
                 for k, v in self.files.items() if k != "RUN401_HEAD.txt"]
        digest = self.make_zip(manifest_override=lines)
        report, checked = self.check(digest)
        self.assertEqual(checked.call_count, 0)
        self.assertIn("UNHASHED_OR_MISSING_MEMBER", str(report["errors"]))

    def test_archive_path_escape_rejected(self):
        digest = self.make_zip(extra={"run401-full/../escape": b"x"})
        report, checked = self.check(digest)
        self.assertEqual(checked.call_count, 0)
        self.assertIn("UNSAFE_ARCHIVE_PATH", str(report["errors"]))

    def test_duplicate_member_rejected(self):
        digest = self.make_zip(duplicates=[("RUN401_HEAD.txt", b"second")])
        report, checked = self.check(digest)
        self.assertEqual(checked.call_count, 0)
        self.assertIn("DUPLICATE_MEMBER", str(report["errors"]))

    def test_symlink_member_rejected(self):
        digest = self.make_zip(symlink="run401-full/RUN397_PROGRESS.json")
        report, checked = self.check(digest)
        self.assertEqual(checked.call_count, 0)
        self.assertIn("SYMLINK_MEMBER", str(report["errors"]))

    def test_model_weights_rejected(self):
        digest = self.make_zip(extra={"run401-full/model.gguf": b"weights"})
        report, checked = self.check(digest)
        self.assertEqual(checked.call_count, 0)
        self.assertIn("MODEL_WEIGHTS_IN_ARTIFACT", str(report["errors"]))

    def test_wrong_zip_sha_rejected_before_extract(self):
        self.make_zip()
        report, checked = self.check("0" * 64)
        self.assertEqual(checked.call_count, 0)
        self.assertIn("ZIP_SHA_MISMATCH", str(report["errors"]))

    def test_size_budget_rejected(self):
        digest = self.make_zip()
        with mock.patch.object(m, "MAX_TOTAL", 10):
            report, checked = self.check(digest)
        self.assertEqual(checked.call_count, 0)
        self.assertIn("TOTAL_UNCOMPRESSED_OVERSIZED", str(report["errors"]))

    def test_existing_symlink_destination_rejected(self):
        digest = self.make_zip()
        target = self.root / "other"
        target.mkdir()
        dest = self.root / "alias"
        dest.symlink_to(target, target_is_directory=True)
        report, checked = self.check(digest, dest)
        self.assertEqual(checked.call_count, 0)
        self.assertIn("DESTINATION_NOT_FRESH", str(report["errors"]))


    def test_atomic_no_replace_installs_fresh_tree(self):
        source = self.root / "stage"
        source.mkdir()
        (source / "sentinel").write_text("stage")
        dest = self.root / "fresh"
        m._rename_noreplace(source, dest)
        self.assertFalse(source.exists())
        self.assertEqual((dest / "sentinel").read_text(), "stage")

    def test_atomic_no_replace_refuses_concurrent_empty_directory(self):
        source = self.root / "stage"
        source.mkdir()
        (source / "sentinel").write_text("stage")
        dest = self.root / "concurrent"
        dest.mkdir()
        (dest / "owner").write_text("other owner")
        with self.assertRaises(FileExistsError):
            m._rename_noreplace(source, dest)
        self.assertTrue(source.is_dir())
        self.assertEqual((dest / "owner").read_text(), "other owner")


if __name__ == "__main__":
    unittest.main()
