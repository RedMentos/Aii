"""Run330 exact-diff guard: original Run327 frozen recipe plus Run329 all-token opt-in and Run328 audit only."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
OLD = ROOT / ".github/workflows/run327-native-lfm2-epochs-repro.yml"
NEW = ROOT / ".github/workflows/run330-native-twoepoch-allloss.yml"

DELTA_BEGIN = "      - name: Independent Run328 actual full GGUF tensor-delta audit (non-promoting)\n"
DELTA_END = "      - name: Official privacy scan\n"


def normalize(candidate):
    text = candidate
    if text.count(DELTA_BEGIN) != 1 or text.count(DELTA_END) != 1:
        raise ValueError("independent delta step missing or ambiguous")
    start = text.index(DELTA_BEGIN)
    end = text.index(DELTA_END, start)
    text = text[:start] + text[end:]
    text = text.replace("          export V13_LOSS_MODE=all\n", "")
    text = text.replace("          test \"${{ steps.delta.outputs.rc }}\" = \"0\"\n", "")
    text = text.replace("            tests.test_run330_exact_recipe \\\n", "")
    text = text.replace("            tests.test_native_all_loss_run329 \\\n", "")
    text = text.replace("      - 'v13/code/tests/test_run330_exact_recipe.py'\n", "")
    text = text.replace("build_native_all_loss_run329.sh", "build_native_answer_epoch_run319.sh")
    text = text.replace("run330-native-twoepoch-allloss/**", "run327-native-lfm2-epochs-repro/**")
    return text.replace("Run330", "Run327").replace("RUN330", "RUN327").replace("run330", "run327")


class Run330ExactRecipe(unittest.TestCase):
    def test_only_explicit_native_loss_compat_and_postflight_changes(self):
        self.assertEqual(normalize(NEW.read_text()), OLD.read_text())

    def test_frozen_model_cohort_source_and_master_still_exact(self):
        text = NEW.read_text()
        for sha in (
            "313bc41c447640241b00319932469345c801f089dae0b949f1f6ebda26d3d53f",
            "dfb46beb7b5be571c364ac3cab04379d411fd54ae5d0005d094f1f5a11e94397",
            "401b95c5c6f4262eb8ea58bdab0af2b79f5d7032951ba45198ab2e13f102858c",
            "1c9c77a4471a7f590f85240f74ed1fc26df7fbde88c3006724e2f93ca993ea4e",
            "5d200c19f13483e66b39d9feb3353032581882f3eb10cc8752f027d4688d6e6f",
            "9e6c6ccf47cd318696e137d381a7ded8fe4df09f",
        ):
            self.assertIn(sha, text)

    def test_all_token_opt_in_and_real_postflight_are_mandatory(self):
        text = NEW.read_text()
        self.assertIn("build_native_all_loss_run329.sh", text)
        self.assertIn("export V13_LOSS_MODE=all", text)
        self.assertIn("scripts/native_lfm2_epoch_eval_run320.py", text)
        self.assertIn("scripts/audit_native_lfm2_epoch_eval_run321.py", text)
        self.assertIn("scripts/audit_native_weight_delta_run328.py", text)
        self.assertIn('test "${{ steps.delta.outputs.rc }}" = "0"', text)

    def test_negative_gates_and_no_weights_uploaded(self):
        text = NEW.read_text()
        self.assertIn("v13-native-c3-run131-serialized", text)
        self.assertIn("never upload weights", text)
        self.assertIn("retention-days: 30", text)


if __name__ == "__main__":
    unittest.main()
