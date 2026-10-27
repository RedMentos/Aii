"""Run635: prospective exact upstream gguf-py exporter dependency contract.

Software-only. No native adapter or learning success is implied.
"""
from pathlib import Path
import hashlib
import unittest

CODE = Path(__file__).resolve().parents[1]
REPO = CODE.parents[1]
WORKFLOW = REPO / '.github/workflows/run635-c3-upstream-gguf-export.yml'


def blob(path):
    b = path.read_bytes()
    return hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest()


class Run635UpstreamGGUF(unittest.TestCase):
    def test_frozen_model_trainer_cohort_and_source_unchanged(self):
        files = {
            'v13/lora_trainer.py': '49a752879ae5d19391963742a0f042e740edb2cc',
            'scripts/run632_c3_lfm350_native.py': 'b59f45f06bf0b8428fba502b8146c02205228edd',
            'docs/proofs/continuation-20261027/run632-c3-lfm350-native/COHORT_V2.json': 'c282077912ec4e284476825b3e03728620d8bad0',
            'specs/models.json': '7af05962af41d0bc3f7dd18ef01d4eba55eabf99',
        }
        for path, sha in files.items():
            with self.subTest(path=path):
                self.assertEqual(blob(CODE / path), sha)

    def test_upstream_release_tar_is_exact_sha_bound(self):
        w = WORKFLOW.read_text()
        self.assertIn('ggml-org/llama.cpp/archive/refs/tags/b10964.tar.gz', w)
        self.assertIn('4c96d72c40cefdacf621457d8a12fe5673b8de5b640ff7fe6d342ea1c579a9fe', w)
        self.assertIn('37420323', w)
        self.assertIn('e54ee5a0fd41416f191130cdf1efd08507f63894', w)
        self.assertIn('d2dfeece59522ffb417f70939cf94ee157591eee', w)

    def test_architecture_and_exact_tensor_mapping_checked_before_fit(self):
        w = WORKFLOW.read_text()
        self.assertIn('gguf.__file__', w)
        self.assertIn('MODEL_ARCH_NAMES', w)
        self.assertIn('get_tensor_name_map', w)
        self.assertIn('model.layers.0.self_attn.v_proj', w)
        self.assertIn('model.layers.0.self_attn.out_proj', w)
        self.assertLess(w.index('RUN635_GGUF_PREFLIGHT_EXIT.txt'),
                        w.index('Actual 2-step LFM2.5-350M CPU LoRA fit'))
        self.assertIn('gguf-py', w)
        self.assertNotIn("'gguf==0.16.3'", w)

    def test_original_native_training_source_and_template_gates_preserved(self):
        w = WORKFLOW.read_text()
        self.assertIn('run632_c3_lfm350_native.py', w)
        self.assertIn('COHORT_V2.json', w)
        self.assertIn('chat_template.jinja', w)
        self.assertIn('return_dict=False', w)
        self.assertIn('public_repo_privacy_scan.py', w)
        self.assertIn('cancel-in-progress: false', w)


if __name__ == '__main__':
    unittest.main()
