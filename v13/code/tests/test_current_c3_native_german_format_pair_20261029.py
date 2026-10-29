"""Software-only prereg checks for unseen Solis German C3 format intervention."""
from pathlib import Path
import tempfile
import unittest

from scripts import current_c3_native_german_format_pair_20261029 as P
from scripts import current_c3_native_bilingual_heldout_20261029 as H


class GermanC3FormatPairTests(unittest.TestCase):
    def test_exact_six_new_paired_cases_and_no_answer_in_format_instruction(self):
        self.assertEqual([r[0] for r in P.CASES], [
            'de_base_present','de_format_present',
            'de_base_absent','de_format_absent',
            'de_base_revised','de_format_revised',
        ])
        self.assertEqual(len({r[1] for r in P.CASES}), 6)
        for name, prompt, target, arm in P.CASES:
            with self.subTest(name=name):
                self.assertIn('Solis', prompt)
                self.assertNotIn('Lumen', prompt)
                self.assertNotIn('Aurora', prompt)
                self.assertEqual(arm, 'FORMAT' if '_format_' in name else 'BASE')
                if arm == 'FORMAT':
                    self.assertIn('genau', prompt)
                    self.assertIn('Keine weiteren', prompt)
                    self.assertNotIn("'180 Euro'", prompt)
                    self.assertNotIn("'65 Euro'", prompt)
                if name.endswith('_absent'):
                    self.assertIsNone(target)
                    self.assertNotIn('180', prompt)
                    self.assertNotIn('65', prompt)
                elif name.endswith('_present'):
                    self.assertEqual(target, 180)
                    self.assertIn('180', prompt)
                    self.assertNotIn('65', prompt)
                else:
                    self.assertEqual(target, 65)
                    self.assertLess(prompt.index('180'), prompt.index('65'))

    def test_same_oracle_for_baseline_and_format(self):
        for arm in ('base','format'):
            self.assertTrue(P.oracle_correct('de_'+arm+'_present', '180 Euro', 180))
            self.assertFalse(P.oracle_correct('de_'+arm+'_present',
                                              'Betrag: 180 Euro\nWaehrung: 0', 180))
            self.assertTrue(P.oracle_correct('de_'+arm+'_revised', '65 Euro', 65))
            self.assertFalse(P.oracle_correct('de_'+arm+'_revised',
                                              '65 Euro und 180 Euro', 65))
            self.assertTrue(P.oracle_correct('de_'+arm+'_absent', 'UNBEKANNT.', None))
            self.assertFalse(P.oracle_correct('de_'+arm+'_absent', 'UNKREID', None))

    def test_generated_only_parser_is_reused_not_prompt_echo(self):
        name, prompt, target, arm = P.CASES[0]
        raw = ('CLI\n\n> '+prompt+'\n180 Euro\n\n[ Prompt: 100.0 t/s | Generation: 80.0 t/s ]\nExiting...').encode()
        generated = H.extract_generated(raw, prompt)
        self.assertEqual(generated, '180 Euro')
        self.assertTrue(P.oracle_correct(name, generated, target))
        self.assertFalse(P.oracle_correct(name, 'UNKNOWN', target))

    def test_official_catalog_and_negative_gates_remain_unchanged(self):
        meta, model, runner = H.prior.pinned._catalog()
        self.assertEqual(meta['model_id'], 'LiquidAI/LFM2.5-350M-GGUF')
        self.assertEqual(model['sha256'], H.prior.pinned.MODEL_SHA)
        self.assertEqual(runner['sha256'], H.prior.pinned.RUNNER_SHA)
        self.assertEqual(H.prior.N_TOKENS, 48)
        self.assertEqual(H.prior.N_CTX, 512)
        self.assertEqual(H.prior.NEGATIVE_GATES['age0'], 'RECORD_ONLY')
        self.assertEqual(H.prior.NEGATIVE_GATES['step2'], 'UTILITY_FAIL')
        self.assertFalse(H.prior.NEGATIVE_GATES['whole_system_complete'])

    def test_existing_scratch_refuses_native_execution(self):
        with tempfile.TemporaryDirectory() as d:
            scratch = Path(d)/'scratch'
            scratch.mkdir()
            with self.assertRaises(FileExistsError):
                P.run(scratch, Path(d)/'evidence')


if __name__ == '__main__':
    unittest.main()
