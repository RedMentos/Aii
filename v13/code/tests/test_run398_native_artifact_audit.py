"""Run398 adversarial ZIP/manifest/native-postflight tests using synthetic rows only."""
import hashlib
import json
import stat
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run398_native_artifact_audit as run398
from tests.test_run396_step2_pilot_audit import make_synthetic


def sha(data):
    return hashlib.sha256(data).hexdigest()


def synthetic_members(folder):
    source = Path(folder) / "native"
    source.mkdir()
    make_synthetic(source)
    files = {"RUN395_HEAD.txt": (run398.RUN395_HEAD + "\n").encode()}
    files.update({name: b"0\n" for name in run398.EXIT_FILES})
    for p in source.glob("*.json"):
        files["run395-pilot/" + p.name] = p.read_bytes()
    return files


def write_zip(path, files, add=None):
    manifest = "".join(sha(data) + "  ./" + name + "\n"
                       for name, data in sorted(files.items()))
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
        z.writestr("RUN395_SHA256SUMS.txt", manifest)
        if add is not None:
            z.writestr(add[0], add[1])
    return sha(Path(path).read_bytes())


class Run398ArtifactAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.files = synthetic_members(self.folder)
        self.path = self.folder / "native-raw.zip"
        self.expected_sha = write_zip(self.path, self.files)

    def test_valid_synthetic_native_shaped_archive_nonpromoting(self):
        r = run398.audit(self.path, self.expected_sha)
        self.assertEqual(r["status"], "PILOT_POSTFLIGHT_VERIFIED")
        self.assertEqual(r["postflight"]["rows_verified"], 42)
        self.assertFalse(r["canonical_gate_pass"])
        self.assertEqual(r["step2_exit"], "UTILITY_FAIL")
        self.assertFalse(r["native_rerun"])

    def test_reject_modified_raw_member_without_manifest_change(self):
        with zipfile.ZipFile(self.path) as z:
            files = {name: z.read(name) for name in z.namelist()}
        files["RUN395_HEAD.txt"] = b"tampered\n"
        with zipfile.ZipFile(self.path, "w", zipfile.ZIP_DEFLATED) as z:
            for name, data in files.items():
                z.writestr(name, data)
        r = run398.audit(self.path)
        self.assertEqual(r["status"], "PILOT_RED_PRESERVED")
        self.assertIn("RAW_SHA_MISMATCH", str(r["errors"]))

    def test_reject_wrong_exact_source_head_even_if_rehashed(self):
        self.files["RUN395_HEAD.txt"] = b"0" * 40 + b"\n"
        write_zip(self.path, self.files)
        r = run398.audit(self.path)
        self.assertIn("RUN395_EXACT_HEAD_MISMATCH", str(r["errors"]))

    def test_reject_missing_native_arm_json_even_if_manifest_updated(self):
        del self.files["run395-pilot/tool_S_s20.json"]
        write_zip(self.path, self.files)
        r = run398.audit(self.path)
        self.assertIn("RUN395_NATIVE_JSON_INCOMPLETE", str(r["errors"]))

    def test_reject_failed_native_exit_even_if_rows_present(self):
        self.files["RUN395_NATIVE_EXIT.txt"] = b"124\n"
        write_zip(self.path, self.files)
        r = run398.audit(self.path)
        self.assertIn("RUN395_PREREQUISITE_OR_NATIVE_RED", str(r["errors"]))

    def test_reject_unsafe_zip_path(self):
        write_zip(self.path, self.files, add=("../escape.txt", b"unsafe"))
        r = run398.audit(self.path)
        self.assertIn("UNSAFE_ZIP_PATH", str(r["errors"]))

    def test_reject_zip_symlink_member_before_extraction(self):
        with zipfile.ZipFile(self.path, "a", zipfile.ZIP_DEFLATED) as z:
            link = zipfile.ZipInfo("run395-pilot/linked.json")
            link.create_system = 3
            link.external_attr = (stat.S_IFLNK | 0o777) << 16
            z.writestr(link, b"RUN395_HEAD.txt")
        r = run398.audit(self.path)
        self.assertIn("SYMLINK_ZIP_MEMBER", str(r["errors"]))

    def test_reject_duplicate_zip_member(self):
        write_zip(self.path, self.files, add=("RUN395_HEAD.txt", b"forged"))
        r = run398.audit(self.path)
        self.assertIn("DUPLICATE_ZIP_MEMBER", str(r["errors"]))

    def test_reject_wrong_expected_zip_sha(self):
        r = run398.audit(self.path, "0" * 64)
        self.assertIn("RAW_ZIP_SHA_MISMATCH", str(r["errors"]))

    def test_reject_truncated_zip_without_raising_or_promoting(self):
        self.path.write_bytes(self.path.read_bytes()[:70])
        r = run398.audit(self.path)
        self.assertEqual(r["status"], "PILOT_RED_PRESERVED")
        self.assertTrue(r["errors"])


if __name__ == "__main__":
    unittest.main()
