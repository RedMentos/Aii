"""Run87 manual native workflow static containment; NO model execution."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github/workflows/v13-run87-b1b2-budget-native-manual.yml"


@unittest.skipUnless(WORKFLOW.is_file(), "repository native workflow unavailable")
class Run87ManualNativeWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_01_explicit_marker_only_no_unscoped_push(self):
        self.assertIn("on:\n  workflow_dispatch:\n  push:", self.text)
        self.assertIn("branches: [assistant/v13-run87-b1b2-budget-ablation-seed877-20261031-gpt6]", self.text)
        self.assertIn("v13/code/docs/RUN87_NATIVE_EXECUTION_TRIGGER_20261031.txt", self.text)
        self.assertNotIn("\n  schedule:", self.text)

    def test_02_shared_serial_heavy_group(self):
        self.assertIn("group: v13-step2-budget-paired-native-20261030", self.text)
        self.assertIn("cancel-in-progress: false", self.text)
        self.assertIn("timeout-minutes: 110", self.text)

    def test_03_pinned_source_and_model_paths(self):
        self.assertIn("v13/code/docs/RUN87_B1B2_BUDGET_ABLATION_NATIVE_PREREG_20261031.md", self.text)
        self.assertIn("v13/code/scripts/jef_b1b2_budget_fixture_877.py", self.text)
        self.assertIn("v13/code/scripts/run87_b1b2_budget_native.py", self.text)
        self.assertIn("v13/code/scripts/run87_b1b2_budget_verify.py", self.text)
        self.assertIn("v13/code/scripts/jef_b1b2_context_fixture_797.py", self.text)
        lines = re.findall(r"^          ([0-9a-f]{40}) (v13/code/\S+)$", self.text, re.M)
        self.assertEqual(len(lines), 14)
        self.assertEqual(len(set(path for _, path in lines)), 14)
        self.assertIn('got="$(git hash-object "$path" 2>/dev/null)"', self.text)

    def test_04_compact_evidence_separate_from_native_home(self):
        self.assertIn('e="$RUNNER_TEMP/v13-run87-compact"', self.text)
        self.assertIn('work="$RUNNER_TEMP/v13-run87-work"', self.text)
        self.assertIn('--out "$work/pilot"', self.text)
        self.assertIn('cp "$work/pilot/report.json" "$e/report.json"', self.text)
        self.assertIn('find "$work/pilot" -name raw_row.json -type f', self.text)
        self.assertNotIn('path: ${{ runner.temp }}/v13-run87-work/', self.text)

    def test_05_original_reds_and_hashes_preserved(self):
        self.assertIn('if [ -f "$work/pilot/report.json" ]; then', self.text)
        self.assertIn('"$e/VERIFY_EXIT.txt"', self.text)
        self.assertIn('! -name SHA256SUMS', self.text)
        self.assertIn('if: always()', self.text)
        self.assertIn('Preserve compact raw evidence, including failed attempts and RED', self.text)
        self.assertIn('NATIVE VERIFY COMPILE PRIVACY DIFF', self.text)

    def test_06_age0_no_training_or_output_activation(self):
        self.assertIn("V13_NO_AUTOSTART: '1'", self.text)
        self.assertIn("DO_NOT_TRACK: '1'", self.text)
        self.assertIn('persist-credentials: false', self.text)
        self.assertNotIn('force-push', self.text)
        self.assertNotIn('git push', self.text)

if __name__ == "__main__":
    unittest.main()
