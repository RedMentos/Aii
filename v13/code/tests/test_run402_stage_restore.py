"""Run402 source-only archive/restore tests. All 42 rows are synthetic, never native proof."""
import hashlib
import json
import shutil
import stat
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run394_step2_fresh as r394
import run397_step2_resume as resume
import run402_stage_restore as restore
from tests.test_run397_step2_resume import synthetic_source, write


def sha(data):
    return hashlib.sha256(data).hexdigest()


def make_archive(folder):
    folder = Path(folder)
    root = folder / "archive"
    work = root / "run401-full"
    attempt = work / "attempts/O_s20/attempt-0001"
    attempt.mkdir(parents=True)
    with patch.object(r394, "PILOT_IDS", tuple(f["id"] for f in r394.FIXTURES)):
        native = synthetic_source(folder / "synthetic-native")
    rid = "O_s20"
    for name in (f"step2_{rid}.json", f"tool_{rid}.json",
                 f"summary_{rid}.json", f"tool_{rid}.preregistration.json"):
        shutil.copyfile(native / name, attempt / name)
    source_path = attempt / f"step2_{rid}.json"
    source = resume.audit.load(source_path)
    source["installed_artifacts"]["runner_sha256"] = restore.RUN401_EXECUTABLE_SHA256
    write(source_path, source)
    prereg_path = attempt / f"tool_{rid}.preregistration.json"
    prereg = resume.audit.load(prereg_path)
    prereg["source_report"]["sha256"] = resume.audit.sha(source_path)
    write(prereg_path, prereg)
    tool_path = attempt / f"tool_{rid}.json"
    tool = resume.audit.load(tool_path)
    tool["preregistration_sha256"] = resume.audit.sha(prereg_path)
    write(tool_path, tool)
    manifest = r394.manifest(r394.FIXTURES, False, list(r394.ARMS), list(r394.SEEDS))
    write(work / "RUN394_PREREGISTERED_FIXTURES.json", manifest)
    verified = resume.validate_completed(attempt, "O", 20, r394.FIXTURES, manifest,
                                          source["installed_artifacts"]["runner_sha256"])
    assert verified["rows"] == 42
    write(attempt / "RUN397_ATTEMPT.json", {"schema": resume.SCHEMA, "status": "COMPLETE",
                                            "arm": "O", "seed": 20, "validated": verified,
                                            "owner": resume.OWNER})
    write(work / "RUN397_PROGRESS.json", {"status": "INCOMPLETE",
                                           "completed": {"O_s20": {
                                               "attempt": "attempts/O_s20/attempt-0001",
                                               "validated": verified}},
                                           "failures_preserved": {},
                                           "canonical_gate_pass": False,
                                           "step2_exit": "UTILITY_FAIL"})
    (work / "RUN397_OWNER.lock").write_bytes(b"")
    (work / "RUN397_EVENTS.jsonl").write_text('{"event":"START","run_id":"O_s20"}\n'
                                                '{"event":"COMPLETE","run_id":"O_s20"}\n')
    write(root / "RUN401_POSTFLIGHT.json", {"stage": "NATIVE_FULL_COHORT_PARTIAL",
                                            "completed": ["O_s20"], "rows_verified": 42,
                                            "remaining_arms": 8, "validated": verified,
                                            "canonical_gate_pass": False,
                                            "step2_exit": "UTILITY_FAIL",
                                            "redmi_measured": False})
    (root / "RUN401_HEAD.txt").write_text(restore.SOURCE_HEAD + "\n")
    (root / "RUN401_INSTALLED_RAW.log").write_text(
        "MODEL_VERIFIED body synthetic\nRUNNER_VERIFIED " +
        restore.RUN401_EXECUTABLE_SHA256 + "\n")
    for name in restore.RAW_EXITS:
        (root / name).write_text("0\n")
    (root / "RUN401_TESTS_RAW.log").write_text("SYNTHETIC TEST ONLY\n")
    return root


def close_archive(root, dest, extra=None, omit=None):
    root, dest = Path(root), Path(dest)
    entries = {}
    for p in root.rglob("*"):
        if p.is_file() and p.name != "RUN401_SHA256SUMS.txt":
            name = p.relative_to(root).as_posix()
            entries[name] = p.read_bytes()
    if omit:
        entries.pop(omit, None)
    if extra:
        entries.update(extra)
    manifest = "".join(f"{sha(data)}  ./{name}\n" for name, data in sorted(entries.items()))
    entries["RUN401_SHA256SUMS.txt"] = manifest.encode()
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in sorted(entries.items()):
            z.writestr(name, data)
    return sha(dest.read_bytes())


class Run402StageRestoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.root = make_archive(self.folder)
        self.archive = self.folder / "source.zip"
        self.expected = close_archive(self.root, self.archive)

    def inspect(self):
        return restore.inspect_archive(self.archive, self.expected)[0]

    def test_synthetic_complete_42_rows_inspects_without_promoting(self):
        r = self.inspect()
        self.assertEqual(r["status"], "STAGE1_RESTORE_VERIFIED", r["errors"])
        self.assertEqual(r["rows_verified"], 42)
        self.assertEqual(r["remaining_arms"], 8)
        self.assertFalse(r["canonical_gate_pass"])

    def test_fresh_atomic_restore_preserves_work_bytes(self):
        dest = self.folder / "restored"
        r = restore.restore_archive(self.archive, self.expected, dest)
        self.assertEqual(r["status"], "STAGE1_RESTORE_VERIFIED", r["errors"])
        self.assertTrue((dest / "attempts/O_s20/attempt-0001/RUN397_ATTEMPT.json").exists())
        for p in (self.root / "run401-full").rglob("*"):
            if p.is_file():
                self.assertEqual(p.read_bytes(), (dest / p.relative_to(self.root / "run401-full")).read_bytes())

    def test_streamed_bytearray_native_runner_log_is_accepted(self):
        files = {p.name: bytearray(p.read_bytes())
                 for p in self.root.glob("RUN401_*") if p.is_file()}
        native = restore._validate_native_tree(self.root / "run401-full", files)
        self.assertEqual(native["rows_verified"], 42)

    def test_streamed_bytearray_forged_runner_log_is_rejected(self):
        files = {p.name: bytearray(p.read_bytes())
                 for p in self.root.glob("RUN401_*") if p.is_file()}
        files["RUN401_INSTALLED_RAW.log"] = bytearray(
            b"RUNNER_VERIFIED " + b"0" * 64 + b"\n")
        with self.assertRaisesRegex(ValueError, "STAGE1_RUNNER_LOG_IDENTITY_MISMATCH"):
            restore._validate_native_tree(self.root / "run401-full", files)

    def test_wrong_expected_sha_rejected(self):
        self.assertEqual(restore.inspect_archive(self.archive, "0" * 64)[0]["status"],
                         "STAGE1_RED_PRESERVED")

    def test_missing_manifest_member_rejected(self):
        self.expected = close_archive(self.root, self.archive,
            omit="run401-full/attempts/O_s20/attempt-0001/tool_O_s20.json")
        self.assertEqual(self.inspect()["status"], "STAGE1_RED_PRESERVED")

    def test_wrong_head_even_if_archive_rehashed(self):
        (self.root / "RUN401_HEAD.txt").write_text("0" * 40 + "\n")
        self.expected = close_archive(self.root, self.archive)
        self.assertIn("HEAD_MISMATCH", " ".join(self.inspect()["errors"]))

    def test_runner_release_tarball_sha_is_not_executable_identity(self):
        wrong = resume.catalog()["runner"]["linux_binaries"]["linux-x86_64"]["sha256"]
        self.assertNotEqual(wrong, restore.RUN401_EXECUTABLE_SHA256)
        (self.root / "RUN401_INSTALLED_RAW.log").write_text("RUNNER_VERIFIED " + wrong + "\n")
        self.expected = close_archive(self.root, self.archive)
        self.assertIn("STAGE1_RUNNER_LOG_IDENTITY_MISMATCH",
                      " ".join(self.inspect()["errors"]))

    def test_missing_installed_runner_log_rejected(self):
        self.expected = close_archive(self.root, self.archive,
                                      omit="RUN401_INSTALLED_RAW.log")
        self.assertIn("STAGE1_RUNNER_LOG", " ".join(self.inspect()["errors"]))

    def test_nonzero_native_exit_rejected(self):
        (self.root / "RUN401_NATIVE_EXIT.txt").write_text("2\n")
        self.expected = close_archive(self.root, self.archive)
        self.assertIn("STAGE1_PREREQUISITE_RED", " ".join(self.inspect()["errors"]))

    def test_forged_completed_receipt_rejected(self):
        p = self.root / "run401-full/attempts/O_s20/attempt-0001/RUN397_ATTEMPT.json"
        data = json.loads(p.read_text())
        data["validated"]["rows"] = 41
        write(p, data)
        self.expected = close_archive(self.root, self.archive)
        self.assertEqual(self.inspect()["status"], "STAGE1_RED_PRESERVED")

    def test_existing_destination_never_overwritten(self):
        dest = self.folder / "existing"
        dest.mkdir()
        sentinel = dest / "KEEP"
        sentinel.write_text("keep")
        r = restore.restore_archive(self.archive, self.expected, dest)
        self.assertEqual(r["status"], "STAGE1_RED_PRESERVED")
        self.assertEqual(sentinel.read_text(), "keep")

    def test_traversal_member_rejected_even_with_matching_manifest(self):
        self.expected = close_archive(self.root, self.archive, extra={"run401-full/../evil": b"evil"})
        self.assertIn("UNSAFE_ARCHIVE_PATH", " ".join(self.inspect()["errors"]))

    def test_symlink_member_rejected(self):
        with zipfile.ZipFile(self.archive, "a") as z:
            info = zipfile.ZipInfo("run401-full/evil-link")
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            z.writestr(info, "../elsewhere")
        self.expected = sha(self.archive.read_bytes())
        self.assertIn("SYMLINK_MEMBER", " ".join(self.inspect()["errors"]))

    def test_duplicate_member_rejected(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(self.archive, "a") as z:
                z.writestr("RUN401_HEAD.txt", restore.SOURCE_HEAD + "\n")
        self.expected = sha(self.archive.read_bytes())
        self.assertIn("DUPLICATE_MEMBER", " ".join(self.inspect()["errors"]))


if __name__ == "__main__":
    unittest.main()
