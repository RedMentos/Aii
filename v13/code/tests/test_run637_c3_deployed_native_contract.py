"""Run637 prospective native workflow contract; no actual model needed for source test."""
from pathlib import Path
import hashlib
import unittest

CODE = Path(__file__).resolve().parents[1]
REPO = CODE.parents[1]
WORKFLOW = REPO / '.github/workflows/run637-c3-deployed-native.yml'


def blob(path):
    b = path.read_bytes()
    return hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest()


class Run637PinnedNative(unittest.TestCase):
    def test_original_evaluator_and_frozen_cohort(self):
        self.assertEqual(blob(CODE / 'scripts/run636_c3_selected_gguf_utility.py'),
                         '8a32d806739f7285ed41232e41168e35cf9ef3eb')
        self.assertEqual(blob(CODE / 'docs/proofs/continuation-20261027/run632-c3-lfm350-native/COHORT_V2.json'),
                         'c282077912ec4e284476825b3e03728620d8bad0')
        self.assertEqual(blob(CODE / 'v13/lora_trainer.py'),
                         '49a752879ae5d19391963742a0f042e740edb2cc')

    def test_original_adapter_archive_and_sha256_bound(self):
        w = WORKFLOW.read_text()
        for token in (
            '12701530582',
            'bd2ffc2969b3b98f8c64a4f776fc7195599a78e74802ace26b59c3dcb576c675',
            '3674e88f71855b46a1de59ca50642ec07c39bb3d6c86bd7e8a49eb1a031d8599',
            'aedbf8d555010882ab2f49a87712a973599dd746fdb1ded1f78b66ebdb4acc2a',
            '4d28ca14dedc0b3d0fcc2b3339f0e79931faa33874f3d24f522183a8fc70068c',
            'RUN632_SHA256SUMS.txt',
        ):
            self.assertIn(token, w)

    def test_official_selected_model_master_server_are_frozen(self):
        w = WORKFLOW.read_text()
        for token in (
            'LiquidAI/LFM2.5-350M-GGUF',
            '657e078c94084481950a2d555a941481f715536b',
            'LFM2.5-350M-QAD-Q4_0.gguf',
            '3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d',
            'LiquidAI/LFM2.5-350M',
            'b6248156b66a93e5c4581d82953a9df630c582ef',
            '1c9c77a4471a7f590f85240f74ed1fc26df7fbde88c3006724e2f93ca993ea4e',
            '013eed60546434b6967e3483153d8c5c37abcb1d667f8b1f914683f2a9411531',
            'llama-b10964-bin-ubuntu-x64.tar.gz',
            '9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443',
            '79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39',
        ):
            self.assertIn(token, w)

    def test_source_gate_before_native_and_no_authority(self):
        w = WORKFLOW.read_text()
        self.assertIn('run636_c3_selected_gguf_utility.py', w)
        self.assertIn('--server-sha', w)
        self.assertIn('public_repo_privacy_scan.py', w)
        self.assertIn('cancel-in-progress: false', w)
        self.assertLess(w.index('RUN637_ADAPTER_EXIT.txt'), w.index('Actual native selected QAD-Q4'))
        self.assertLess(w.index('RUN637_MODEL_EXIT.txt'), w.index('Actual native selected QAD-Q4'))
        self.assertLess(w.index('RUN637_SERVER_EXIT.txt'), w.index('Actual native selected QAD-Q4'))


if __name__ == '__main__':
    unittest.main()
