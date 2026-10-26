"""Run470 end-to-end synthetic pinned replay tests; no native execution."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run469_native378_utility as base
import run470_step2_complementarity as candidate
from tests.test_run469_native378_pinned_reads import PinnedUtilityReads


class Run470PinnedReplay(unittest.TestCase):
    def setUp(self):
        self.fixture = PinnedUtilityReads(
            methodName="test_unchanged_attested_export_is_readable_without_gate_promotion")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    @staticmethod
    def fake_rows(tool, expected, label):
        return {key: {"score": {"utility": tool["utility"]}} for key in expected}

    def run_candidate(self, mutate_after_first=None):
        fixture = self.fixture
        original = base.analyze

        def verified(root, report):
            self.assertEqual(Path(root), fixture.root)
            return fixture.checked

        def first_pass(*args):
            result = original(*args)
            if mutate_after_first is not None:
                mutate_after_first()
            return result

        with (patch.object(base.verified378, "verify", side_effect=verified),
              patch.object(base, "validated_rows", side_effect=self.fake_rows),
              patch.object(base, "analyze", side_effect=first_pass)):
            return candidate.analyze(fixture.root, {})

    def test_full_synthetic_export_replayed_with_all_attested_reads(self):
        report = self.run_candidate()
        self.assertEqual(report["rows"], 378)
        self.assertEqual(report["status"],
                         "RUN470_FROZEN_COHORT_COMPLEMENTARITY_DIAGNOSTIC_ONLY")
        self.assertEqual(report["manifest_sha256"], self.fixture.checked["manifest_sha256"])
        self.assertEqual(report["progress_sha256"], self.fixture.checked["progress_sha256"])
        self.assertFalse(report["canonical_gate_pass"])
        self.assertEqual(report["step2_exit"], "UTILITY_FAIL")

    def test_post_first_pass_tool_tamper_cannot_change_complementarity(self):
        path = self.fixture.root / "attempts/P_s20/attempt-1/tool_P_s20.json"
        def tamper():
            data = path.read_bytes()
            self.assertIn(b"0.6", data)
            path.write_bytes(data.replace(b"0.6", b"0.9"))
        with self.assertRaisesRegex(ValueError, "PINNED_READ_HASH_CHANGED"):
            self.run_candidate(tamper)

    def test_post_first_pass_manifest_tamper_refused(self):
        def tamper():
            self.fixture.manifest_path.write_bytes(b'{"copied":{}}\n')
        with self.assertRaisesRegex(ValueError, "PINNED_READ_HASH_CHANGED"):
            self.run_candidate(tamper)

    def test_post_first_pass_progress_tamper_refused(self):
        path = self.fixture.root / "RUN397_PROGRESS.json"
        def tamper():
            path.write_bytes(path.read_bytes().replace(b"P_s22", b"X_s22"))
        with self.assertRaisesRegex(ValueError, "PINNED_READ_HASH_CHANGED"):
            self.run_candidate(tamper)


if __name__ == "__main__":
    unittest.main()
