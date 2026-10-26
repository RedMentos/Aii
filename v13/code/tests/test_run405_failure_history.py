"""Run405 RED-first: a complete synthetic cohort must not hide missing failed attempts."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run403_full_postflight as audit
from tests.test_run403_full_postflight import make_full, write


class Run405FailureHistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = make_full(Path(self.tmp.name))
        self.progress = self.work / "RUN397_PROGRESS.json"

    def add_failure(self, arm, path, reason="NO_COMPLETED_RECEIPT"):
        p = json.loads(self.progress.read_text())
        p["failures_preserved"] = {arm: [{"attempt": path, "reason": reason}]}
        write(self.progress, p)

    def test_missing_failed_attempt_directory_is_not_silently_green(self):
        self.add_failure("P_s20", "attempts/P_s20/attempt-0000")
        r = audit.audit(self.work)
        self.assertEqual(r["status"], "FULL_INCOMPLETE_OR_RED", r)

    def test_existing_failed_attempt_is_preserved_and_reported(self):
        d = self.work / "attempts/P_s20/attempt-0000"
        d.mkdir(parents=True)
        (d / "RUN397_FAILED.json").write_text('{"event":"FAILED","run_id":"P_s20"}\n')
        self.add_failure("P_s20", "attempts/P_s20/attempt-0000")
        r = audit.audit(self.work)
        self.assertEqual(r["status"], "FULL_POSTFLIGHT_VERIFIED_NO_GATE_PROMOTION", r.get("errors"))
        self.assertEqual(r["failed_attempts_preserved"]["P_s20"][0]["attempt"],
                         "attempts/P_s20/attempt-0000")
        self.assertTrue((d / "RUN397_FAILED.json").exists())

    def test_unsafe_failure_path_is_rejected(self):
        self.add_failure("P_s20", "../outside")
        self.assertEqual(audit.audit(self.work)["status"], "FULL_INCOMPLETE_OR_RED")

    def test_unknown_arm_failure_is_rejected(self):
        self.add_failure("X_s20", "attempts/X_s20/attempt-0001")
        self.assertEqual(audit.audit(self.work)["status"], "FULL_INCOMPLETE_OR_RED")

    def test_empty_failed_attempt_is_rejected(self):
        d = self.work / "attempts/P_s20/attempt-0000"
        d.mkdir(parents=True)
        self.add_failure("P_s20", "attempts/P_s20/attempt-0000")
        self.assertEqual(audit.audit(self.work)["status"], "FULL_INCOMPLETE_OR_RED")

    def test_symlinked_failed_attempt_is_rejected(self):
        target = self.work / "external"
        target.mkdir()
        (target / "partial.json").write_text("{}")
        (self.work / "attempts/P_s20/attempt-0000").symlink_to(target, target_is_directory=True)
        self.add_failure("P_s20", "attempts/P_s20/attempt-0000")
        self.assertEqual(audit.audit(self.work)["status"], "FULL_INCOMPLETE_OR_RED")


if __name__ == "__main__":
    unittest.main()
