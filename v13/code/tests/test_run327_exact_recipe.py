"""Run327 exact source-only guard: original Run325 workflow plus conversion prerequisite ONLY."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
ORIGINAL = ROOT / ".github/workflows/run325-native-lfm2-epochs.yml"
CANDIDATE = ROOT / ".github/workflows/run327-native-lfm2-epochs-repro.yml"


def expected(original):
    text = original.replace("Run325", "Run327").replace("RUN325", "RUN327").replace("run325", "run327")
    text = text.replace("run327hf", "run324hf")
    text = text.replace("run327-master-f32.gguf", "run324-f32.gguf")
    text = text.replace("'chat_template.jinja','LICENSE','generation_config.json'",
                        "'special_tokens_map.json','chat_template.jinja','generation_config.json'")
    text = text.replace("native-lfm2-epochs-run327/**", "run327-native-lfm2-epochs-repro/**")
    text = text.replace("      - 'v13/code/tests/test_native_lfm2_epoch_eval_run320.py'",
                        "      - 'v13/code/tests/test_native_lfm2_epoch_eval_run320.py'\n"
                        "      - 'v13/code/tests/test_run327_exact_recipe.py'")
    text = text.replace("            tests.test_native_lfm2_epoch_eval_run320 \\\n",
                        "            tests.test_native_lfm2_epoch_eval_run320 \\\n"
                        "            tests.test_run327_exact_recipe \\\n")
    return text


class Run327ExactRecipe(unittest.TestCase):
    def test_exact_diff_only_permitted_prerequisite_and_workflow_naming(self):
        old = ORIGINAL.read_text()
        new = CANDIDATE.read_text()
        self.assertEqual(new, expected(old))

    def test_original_train_and_evaluator_source_hashes_unchanged(self):
        old = ORIGINAL.read_text()
        new = CANDIDATE.read_text()
        for frozen in (
            "313bc41c447640241b00319932469345c801f089dae0b949f1f6ebda26d3d53f",
            "dfb46beb7b5be571c364ac3cab04379d411fd54ae5d0005d094f1f5a11e94397",
            "401b95c5c6f4262eb8ea58bdab0af2b79f5d7032951ba45198ab2e13f102858c",
            "9e6c6ccf47cd318696e137d381a7ded8fe4df09f",
            "5d200c19f13483e66b39d9feb3353032581882f3eb10cc8752f027d4688d6e6f",
            "1c9c77a4471a7f590f85240f74ed1fc26df7fbde88c3006724e2f93ca993ea4e",
        ):
            self.assertIn(frozen, old)
            self.assertIn(frozen, new)

    def test_original_evaluator_and_postflight_commands_preserved(self):
        new = CANDIDATE.read_text()
        for text in ("scripts/native_lfm2_epoch_eval_run320.py",
                     "scripts/audit_native_lfm2_epoch_eval_run321.py",
                     "--source-manifest", "--out-dir",
                     "V13_EPOCH_CHECKPOINTS", "run324-f32.gguf"):
            if text == "V13_EPOCH_CHECKPOINTS":
                continue  # trainer controls this internally in the unchanged original evaluator
            self.assertIn(text, new)

    def test_original_failure_not_relabelled_as_success(self):
        new = CANDIDATE.read_text()
        self.assertIn('test "${{ steps.model.outputs.rc }}" = "0"', new)
        self.assertIn('test "${{ steps.native.outputs.rc }}" = "0"', new)
        self.assertIn('test "${{ steps.audit.outputs.rc }}" = "0"', new)
        self.assertIn("v13-native-c3-run131-serialized", new)


if __name__ == "__main__":
    unittest.main()
