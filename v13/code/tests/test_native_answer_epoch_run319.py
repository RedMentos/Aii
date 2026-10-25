"""Run319 source-only native epoch checkpoint preparation (not weight training)."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts import prepare_native_answer_epoch_run319 as P

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'scripts/native_answer_finetune.cpp'
PATCH = ROOT / 'scripts/patches/native-answer-epoch-checkpoint-run319.patch'


class NativeAnswerEpochRun319(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
    def tearDown(self):
        self.tmp.cleanup()

    def test_exact_registered_source_and_isolated_patch(self):
        self.assertEqual(P.digest(SOURCE), P.ORIGINAL_SHA256)
        original = SOURCE.read_bytes()
        report = P.prepare(SOURCE, PATCH, self.root / 'candidate')
        self.assertEqual(report['status'], 'SOURCE_PREPARED_NO_NATIVE_TRAINING')
        self.assertTrue(report['original_unchanged'])
        self.assertFalse(report['native_compiled'])
        self.assertFalse(report['native_trained'])
        self.assertEqual(SOURCE.read_bytes(), original)
        candidate = self.root / 'candidate/scripts/native_answer_finetune.cpp'
        self.assertNotEqual(P.digest(candidate), P.ORIGINAL_SHA256)
        self.assertEqual(P.digest(candidate), report['candidate_sha256'])
        self.assertEqual(json.loads((self.root / 'candidate/RUN319_PREP.json').read_text())['gates']['jepa_weight'], 0)

    def test_default_disabled_and_bounded_fail_closed_candidate(self):
        P.prepare(SOURCE, PATCH, self.root / 'candidate')
        code = (self.root / 'candidate/scripts/native_answer_finetune.cpp').read_text()
        self.assertIn('epoch_env && std::strcmp(epoch_env, "1") == 0', code)
        self.assertIn('lr.epochs < 1 || lr.epochs > 8', code)
        self.assertIn('std::filesystem::is_symlink', code)
        self.assertIn('std::filesystem::file_size', code)
        self.assertIn('llama_model_save_to_file(model, path.c_str())', code)
        self.assertEqual(code.count('V13_EPOCH_CHECKPOINT {'), 1)
        self.assertIn('llama_model_save_to_file(model, params.out_file.c_str())', code)

    def test_refuse_output_overwrite_and_no_source_mutation(self):
        dest = self.root / 'candidate'
        P.prepare(SOURCE, PATCH, dest)
        prior = (dest / 'RUN319_PREP.json').read_bytes()
        with self.assertRaises(FileExistsError):
            P.prepare(SOURCE, PATCH, dest)
        self.assertEqual((dest / 'RUN319_PREP.json').read_bytes(), prior)
        self.assertEqual(P.digest(SOURCE), P.ORIGINAL_SHA256)

    def test_refuse_drifted_original_even_if_patch_could_apply(self):
        source = self.root / 'drift.cpp'
        shutil.copyfile(SOURCE, source)
        source.write_bytes(source.read_bytes() + b'\n// drift\n')
        with self.assertRaisesRegex(ValueError, 'SHA drift'):
            P.prepare(source, PATCH, self.root / 'candidate')
        self.assertFalse((self.root / 'candidate').exists())

    def test_refuse_modified_patch_and_keep_original(self):
        patch = self.root / 'wrong.patch'
        patch.write_text(PATCH.read_text().replace('native_answer_finetune.cpp',
                                                   'different_file.cpp'))
        with self.assertRaisesRegex(ValueError, 'expected original'):
            P.prepare(SOURCE, patch, self.root / 'candidate')
        self.assertEqual(P.digest(SOURCE), P.ORIGINAL_SHA256)

    def test_no_native_claim_from_source_only(self):
        report = P.prepare(SOURCE, PATCH, self.root / 'candidate')
        self.assertFalse(report['model_weight_activation'])
        self.assertEqual(report['gates']['Body_JEPA'], 'UNAVAILABLE')
        self.assertEqual(report['gates']['STEP2'], 'UTILITY_FAIL')
        self.assertFalse(report['overwrite_allowed'])


if __name__ == '__main__':
    unittest.main()
