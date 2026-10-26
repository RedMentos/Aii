"""Run404 source-only stage2 orchestration tests; no real model/native execution."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run397_step2_resume as resume
import run404_stage2_resume as stage
from tests.test_run402_stage_restore import make_archive, close_archive


class Run404Stage2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.root = make_archive(self.folder)
        self.archive = self.folder / "observed-SYNTHETIC.zip"
        self.sha = close_archive(self.root, self.archive)
        self.work = self.folder / "restored"

    def test_preview_restores_one_42_row_receipt_without_running_native(self):
        with patch.object(resume, "run", side_effect=AssertionError("NATIVE_MUST_NOT_RUN")):
            r = stage.stage2(self.archive, self.sha, self.work)
        self.assertEqual(r["status"], "STAGE2_READY_NO_NATIVE", r["errors"])
        self.assertEqual(r["completed"], ["O_s20"])
        self.assertEqual(r["rows_verified"], 42)
        self.assertFalse(r["native_execute_attempted"])
        self.assertFalse(r["native_execution_performed"])
        self.assertFalse(r["canonical_gate_pass"])

    def test_preview_preserves_original_stage1_journal_and_receipt_bytes(self):
        original = self.root / "run401-full"
        r = stage.stage2(self.archive, self.sha, self.work)
        self.assertEqual(r["status"], "STAGE2_READY_NO_NATIVE", r["errors"])
        for rel in ("RUN397_EVENTS.jsonl", "RUN397_PROGRESS.json",
                    "attempts/O_s20/attempt-0001/RUN397_ATTEMPT.json"):
            self.assertEqual((original / rel).read_bytes(), (self.work / rel).read_bytes())

    def test_wrong_sha_fails_before_creating_destination(self):
        r = stage.stage2(self.archive, "0" * 64, self.work)
        self.assertEqual(r["status"], "STAGE2_RED_PRESERVED")
        self.assertFalse(self.work.exists())

    def test_existing_work_is_never_overwritten(self):
        self.work.mkdir()
        (self.work / "KEEP").write_text("keep")
        r = stage.stage2(self.archive, self.sha, self.work)
        self.assertEqual(r["status"], "STAGE2_RED_PRESERVED")
        self.assertEqual((self.work / "KEEP").read_text(), "keep")

    def test_execute_without_installed_home_fails_before_restore(self):
        r = stage.stage2(self.archive, self.sha, self.work, execute=True)
        self.assertEqual(r["status"], "STAGE2_RED_PRESERVED")
        self.assertIn("INSTALLED_HOME_REQUIRED", " ".join(r["errors"]))
        self.assertFalse(self.work.exists())

    def test_mocked_stage2_calls_one_new_arm_and_keeps_gate_red(self):
        original_validate = resume.validate_completed
        def validate(directory, arm, seed, fixtures, manifest, current_runner_sha=None):
            if arm == "P":
                return {"rows": 42}
            return original_validate(directory, arm, seed, fixtures, manifest,
                                     current_runner_sha=current_runner_sha)
        calls = []
        def fake_run(work, installed, pilot, execute, max_new_arms):
            calls.append((pilot, execute, max_new_arms))
            p = Path(work)
            progress = json.loads((p / "RUN397_PROGRESS.json").read_text())
            progress["completed"]["P_s20"] = {
                "attempt": "attempts/P_s20/attempt-0001", "validated": {"rows": 42}}
            (p / "RUN397_PROGRESS.json").write_text(json.dumps(progress))
            return progress
        with patch.object(resume, "run", side_effect=fake_run), \
             patch.object(resume, "validate_completed", side_effect=validate):
            r = stage.stage2(self.archive, self.sha, self.work,
                             installed=self.folder / "FAKE_NO_MODEL", execute=True)
        self.assertEqual(calls, [(False, True, 1)])
        self.assertEqual(r["status"], "STAGE2_NATIVE_PARTIAL_NO_GATE_PROMOTION", r["errors"])
        self.assertEqual(r["rows_verified"], 84)
        self.assertEqual(r["remaining_arms"], 7)
        self.assertTrue(r["native_execution_performed"])
        self.assertFalse(r["native_rerun"])
        self.assertFalse(r["canonical_gate_pass"])

    def test_mocked_wrong_next_arm_rejected(self):
        def wrong_run(work, installed, pilot, execute, max_new_arms):
            progress = json.loads((Path(work) / "RUN397_PROGRESS.json").read_text())
            progress["completed"]["S_s20"] = {"attempt": "attempts/S_s20/attempt-0001"}
            return progress
        with patch.object(resume, "run", side_effect=wrong_run):
            r = stage.stage2(self.archive, self.sha, self.work,
                             installed=self.folder / "FAKE_NO_MODEL", execute=True)
        self.assertEqual(r["status"], "STAGE2_RED_PRESERVED")
        self.assertTrue(r["native_execute_attempted"])
        self.assertFalse(r["native_execution_performed"])

    def test_mocked_native_exception_keeps_restored_work_and_red(self):
        with patch.object(resume, "run", side_effect=RuntimeError("SYNTHETIC_NATIVE_FAILURE")):
            r = stage.stage2(self.archive, self.sha, self.work,
                             installed=self.folder / "FAKE_NO_MODEL", execute=True)
        self.assertEqual(r["status"], "STAGE2_RED_PRESERVED")
        self.assertTrue((self.work / "RUN397_PROGRESS.json").exists())
        self.assertIn("SYNTHETIC_NATIVE_FAILURE", " ".join(r["errors"]))


if __name__ == "__main__":
    unittest.main()
