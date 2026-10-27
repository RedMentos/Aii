"""Run634: prospective source-only contract for exact official C3 Jinja retrieval.

The model run itself is Linux-native Actions evidence, not asserted here.
"""
from pathlib import Path
import hashlib
import unittest

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
WORKFLOW = REPO / '.github/workflows/run634-c3-pinned-chat-template.yml'
SCRIPT = ROOT / 'scripts/run632_c3_lfm350_native.py'
TRAINER = ROOT / 'v13/lora_trainer.py'
COHORT = ROOT / 'docs/proofs/continuation-20261027/run632-c3-lfm350-native/COHORT_V2.json'
SPEC = ROOT / 'specs/models.json'


def blob(path):
    raw = path.read_bytes()
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


class Run634PinnedTemplate(unittest.TestCase):
    def test_original_frozen_source_cohort_and_model_manifest_unchanged(self):
        self.assertEqual(blob(SCRIPT), 'b59f45f06bf0b8428fba502b8146c02205228edd')
        self.assertEqual(blob(TRAINER), '49a752879ae5d19391963742a0f042e740edb2cc')
        self.assertEqual(blob(COHORT), 'c282077912ec4e284476825b3e03728620d8bad0')
        self.assertEqual(blob(SPEC), '7af05962af41d0bc3f7dd18ef01d4eba55eabf99')

    def test_only_exact_official_template_is_added_to_pinned_download(self):
        w = WORKFLOW.read_text()
        self.assertIn("revision='b6248156b66a93e5c4581d82953a9df630c582ef'", w)
        self.assertIn("repo_id='LiquidAI/LFM2.5-350M'", w)
        self.assertIn("'chat_template.jinja'", w)
        self.assertIn("'model.safetensors'", w)
        self.assertNotIn("allow_patterns=['*']", w)
        self.assertIn("MASTER_SHA256_PASS", w)

    def test_tokenizer_template_and_token_ids_are_checked_before_fit(self):
        w = WORKFLOW.read_text()
        self.assertIn("AutoTokenizer.from_pretrained", w)
        self.assertIn("tok.chat_template", w)
        self.assertIn("tok.apply_chat_template", w)
        self.assertIn("add_generation_prompt=True", w)
        self.assertIn("add_special_tokens=False", w)
        # Transformers 5 returns BatchEncoding by default, not list[int].
        self.assertIn("return_dict=False", w)
        self.assertIn("chat_template.jinja", w)
        self.assertIn("RUN634_TEMPLATE_EXIT.txt", w)
        self.assertLess(w.index("RUN634_TEMPLATE_EXIT.txt"), w.index("Actual 2-step LFM2.5-350M CPU LoRA fit"))

    def test_run634_no_production_authority_or_cohort_changes(self):
        w = WORKFLOW.read_text()
        self.assertIn("run632_c3_lfm350_native.py", w)
        self.assertIn("COHORT_V2.json", w)
        self.assertIn("jepa_weight", (ROOT / 'docs/proofs/continuation-20261027/run632-c3-lfm350-native/PREREG.md').read_text())
        self.assertIn("concurrency:", w)
        self.assertIn("cancel-in-progress: false", w)
        self.assertIn("public_repo_privacy_scan.py", w)


if __name__ == '__main__':
    unittest.main()
