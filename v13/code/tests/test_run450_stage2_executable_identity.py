"""Run450 RED-first: Run404 must compare native executable SHA, not release ZIP SHA.

Historical synthetic Run401 receipt intentionally records the actual executable
identity. This does not change the frozen runner/model/seed cohort or run native.
"""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run402_stage_restore as restore
import run404_stage2_resume as stage
from tests.test_run402_stage_restore import make_archive, close_archive
from v13.models import catalog


class Run450ExecutableIdentityTests(unittest.TestCase):
    def test_valid_stage1_executable_receipt_is_reusable_in_stage2_preview(self):
        release_archive_sha = catalog()["runner"]["linux_binaries"]["linux-x86_64"]["sha256"]
        self.assertNotEqual(release_archive_sha, restore.RUN401_EXECUTABLE_SHA256)
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            root = make_archive(folder)
            archive = folder / "synthetic-stage1.zip"
            sha = close_archive(root, archive)
            result = stage.stage2(archive, sha, folder / "restored")
            self.assertEqual(result["status"], "STAGE2_READY_NO_NATIVE", result["errors"])
            self.assertEqual(result["rows_verified"], 42)
            self.assertFalse(result["native_execution_performed"])
            self.assertFalse(result["canonical_gate_pass"])
            self.assertEqual(result["step2_exit"], "UTILITY_FAIL")


if __name__ == "__main__":
    unittest.main()
