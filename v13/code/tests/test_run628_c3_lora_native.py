"""Run628: independent source-only frozen cohort and master tamper controls."""
import json
import tempfile
import unittest
from pathlib import Path
from scripts import run628_c3_lora_native as R

COHORT = Path(__file__).resolve().parents[1] / 'docs/proofs/continuation-20261027/run628-c3-native-lora/COHORT.json'


class PinnedC3MasterContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'cohort.json'
        self.data = json.loads(COHORT.read_text())
        self.path.write_text(json.dumps(self.data))

    def tearDown(self):
        self.tmp.cleanup()

    def change(self, fn):
        d = json.loads(self.path.read_text())
        fn(d)
        self.path.write_text(json.dumps(d))
        return self.path

    def test_frozen_real_public_master_and_train_holdout_disjoint(self):
        d = R.cohort_load(COHORT)
        self.assertEqual(d['model']['revision'], R.MODEL_REV)
        self.assertEqual(d['model']['master_sha256'], R.MODEL_SHA)
        self.assertEqual(d['model']['license'], 'apache-2.0')
        self.assertFalse(set(x['prompt'] for x in d['train']) & set(x['prompt'] for x in d['heldout']))
        self.assertEqual(d['config']['jepa_weight'], 0)

    def test_model_revision_and_sha_tampering_rejected(self):
        for field, value in [('revision', 'main'), ('master_sha256', '0' * 64), ('license', 'unknown')]:
            with self.subTest(field=field):
                self.path.write_text(json.dumps(self.data))
                self.change(lambda d: d['model'].__setitem__(field, value))
                with self.assertRaisesRegex(ValueError, 'model revision/hash/license'):
                    R.cohort_load(self.path)

    def test_train_holdout_leak_and_unapproved_jepa_rejected(self):
        self.change(lambda d: d['heldout'][0].__setitem__('prompt', d['train'][0]['prompt']))
        with self.assertRaisesRegex(ValueError, 'overlap'):
            R.cohort_load(self.path)
        self.path.write_text(json.dumps(self.data))
        self.change(lambda d: d['config'].__setitem__('jepa_weight', 0.1))
        with self.assertRaisesRegex(ValueError, 'unapproved'):
            R.cohort_load(self.path)

    def test_missing_or_tampered_master_rejected_before_torch_import(self):
        d = R.cohort_load(COHORT)
        home = Path(self.tmp.name) / 'model'
        home.mkdir()
        with self.assertRaisesRegex(ValueError, 'master SHA256 mismatch'):
            R.master_check(home, d)
        (home / 'model.safetensors').write_bytes(b'tampered')
        (home / 'config.json').write_text('{"model_type":"llama","architectures":["LlamaForCausalLM"]}')
        with self.assertRaisesRegex(ValueError, 'master SHA256 mismatch'):
            R.master_check(home, d)


if __name__ == '__main__':
    unittest.main()
