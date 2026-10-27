from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]
WF = ROOT / ".github" / "workflows" / "bp1-qad-train-plus-v2-samejob.yml"


class AdapterLocatorWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WF.read_text(encoding="utf-8")

    def test_retry_only_new_branch_and_activation(self):
        self.assertIn("branches: [codex/automation11-bp1-v2-adapter-locator-retry-20261027]", self.text)
        self.assertIn("bp1-qad-train-v2-samejob/ACTIVATE_RETRY.txt", self.text)
        self.assertNotIn("bp1-qad-train-v2-samejob/ACTIVATE.txt", self.text)

    def test_exact_trainer_work_locator_before_binding(self):
        locator = self.text.index("v13/code/scripts/bp1_qad_adapter_locator.py --trainer-work")
        binding = self.text.index('> "$RUNNER_TEMP/bp1-native-train/V2_BINDING_RAW.log"')
        self.assertLess(locator, binding)
        self.assertIn('V2_ADAPTER_LOCATOR_EXIT.txt', self.text)
        self.assertIn('V2_ADAPTER_PATH.txt', self.text)
        self.assertIn('V2_ADAPTER_LOCATOR V2; do', self.text)

    def test_actual_adapter_path_used_by_binding_and_collector(self):
        self.assertIn('adapter=Path((tmp/"bp1-native-train"/"V2_ADAPTER_PATH.txt").read_text().strip())', self.text)
        self.assertIn('--adapter-gguf "$(cat "$RUNNER_TEMP/bp1-native-train/V2_ADAPTER_PATH.txt")"', self.text)
        self.assertNotIn('bp1-train-output/adapter.gguf', self.text)

    def test_no_weights_in_uploaded_artifacts(self):
        self.assertIn('path: ${{ runner.temp }}/bp1-native-train/', self.text)
        self.assertNotIn('path: ${{ runner.temp }}/bp1-train-output/', self.text)
        self.assertNotIn('cp "$RUNNER_TEMP/bp1-train-output/trainer-work"', self.text)
        self.assertIn('Never copy adapter.gguf or safetensors', self.text)

    def test_pinned_original_train_and_heldout_unchanged(self):
        self.assertIn('9f356917911983e887f80aaadd8b58365fe43ecbf6632bb5e9e0a1aa8628ff86', self.text)
        self.assertIn('7238a0220255cbccbcf1f9ccfad8dc03febfc37f7bc1d9d0aa645618f006508c', self.text)
        self.assertIn('3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d', self.text)
        self.assertIn('concurrency:', self.text)
        self.assertIn('group: v13-bp1-qad-native-smoke-heavy-serial', self.text)


if __name__ == "__main__":
    unittest.main()
