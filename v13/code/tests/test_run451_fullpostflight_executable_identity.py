"""Run451 RED-first: full synthetic Run403 cohort uses the installed executable SHA.

The Run401 O_s20 receipt and every later synthetic arm must refer to the same
pinned executable, not a mix of executable and release-archive hashes.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run402_stage_restore as restore
import run403_full_postflight as audit
from tests.test_run403_full_postflight import make_full
from v13.models import catalog


class Run451FullPostflightExecutableIdentity(unittest.TestCase):
    def test_all_nine_synthetic_receipts_share_installed_executable_identity(self):
        release_sha = catalog()["runner"]["linux_binaries"]["linux-x86_64"]["sha256"]
        self.assertNotEqual(release_sha, restore.RUN401_EXECUTABLE_SHA256)
        with tempfile.TemporaryDirectory() as tmp:
            work = make_full(Path(tmp))
            hashes = set()
            for seed in (20, 21, 22):
                for arm in ("O", "P", "S"):
                    rid = f"{arm}_s{seed}"
                    path = work / "attempts" / rid / "attempt-0001" / f"step2_{rid}.json"
                    report = json.loads(path.read_text())
                    hashes.add(report["installed_artifacts"]["runner_sha256"])
            self.assertEqual(hashes, {restore.RUN401_EXECUTABLE_SHA256})
            result = audit.audit(work)
            self.assertEqual(result["status"], "FULL_POSTFLIGHT_VERIFIED_NO_GATE_PROMOTION",
                             result.get("errors"))
            self.assertEqual(result["rows_verified"], 378)
            self.assertFalse(result["canonical_gate_pass"])
            self.assertEqual(result["step2_exit"], "UTILITY_FAIL")
            self.assertEqual(result["jepa_weight"], 0)
            self.assertFalse(result["redmi_measured"])


if __name__ == "__main__":
    unittest.main()
