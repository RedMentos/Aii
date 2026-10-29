"""Frozen generated-only and exact oracle software tests for unseen C3 heldout.

No native download/inference. Synthetic stdout controls are not scored as
native evidence. Fixed heldout prompts were registered before native output.
"""
from pathlib import Path
import tempfile
import unittest

from scripts import current_c3_native_bilingual_heldout_20261029 as H


class C3BilingualHeldoutOracleTests(unittest.TestCase):
    def test_exact_six_heldout_cohort(self):
        self.assertEqual([x[0] for x in H.CASES], [
            'en_present', 'en_absent', 'en_revised',
            'de_present', 'de_absent', 'de_revised',
        ])
        self.assertEqual(len({x[1] for x in H.CASES}), 6)
        for name, prompt, target in H.CASES:
            with self.subTest(name=name):
                self.assertIn('Lumen', prompt)
                self.assertNotIn('Aurora', prompt)
                if name.endswith('_absent'):
                    self.assertIsNone(target)
                    self.assertNotIn('160', prompt)
                    self.assertNotIn('75', prompt)
                elif name.endswith('_present'):
                    self.assertEqual(target, 160)
                    self.assertIn('160', prompt)
                    self.assertNotIn('75', prompt)
                else:
                    self.assertEqual(target, 75)
                    self.assertLess(prompt.index('160'), prompt.index('75'))

    def test_generated_only_parser_excludes_exact_prompt_echo(self):
        prompt = H.CASES[0][1]
        raw = ('CLI banner\n\n> ' + prompt + '\n120 euros'
               '\n\n[ Prompt: 242.5 t/s | Generation: 108.1 t/s ]'
               '\n\n\nExiting...\n').encode()
        self.assertEqual(H.extract_generated(raw, prompt), '120 euros')
        self.assertTrue(H.oracle_correct('en_present',
                                         H.extract_generated(raw, prompt), 160))
        # The raw prompt itself contains 160, but is never scored.
        self.assertFalse(H.oracle_correct('en_present', 'UNKNOWN', 160))

    def test_parser_rejects_missing_duplicate_or_incomplete_boundaries(self):
        prompt = H.CASES[0][1]
        anchor = '\n\n> ' + prompt + '\n'
        footer = '\n\n[ Prompt: 242.5 t/s | Generation: 108.1 t/s ]'
        valid = ('banner' + anchor + '160 euros' + footer + '\nExiting...').encode()
        for raw in (
            b'banner 160 euros',
            ('banner' + anchor + '160 euros').encode(),
            ('banner' + anchor + '160 euros' + footer).encode(),
            ('banner' + anchor + '160 euros' + footer + footer + '\nExiting...').encode(),
            ('banner' + anchor + anchor + '160 euros' + footer + '\nExiting...').encode(),
            ('banner' + anchor + prompt + footer + '\nExiting...').encode(),
            valid + b'\xff',
        ):
            with self.subTest(raw=raw[:40]):
                with self.assertRaises((ValueError, UnicodeError)):
                    H.extract_generated(raw, prompt)

    def test_amount_oracle_rejects_extra_numbers_and_wrong_revision(self):
        for name, target, answer, expected in (
            ('en_present', 160, '160 euros', True),
            ('en_present', 160, '160 euros and 30 euros', False),
            ('en_present', 160, '160', False),
            ('en_present', 160, '160 euros UNKNOWN', False),
            ('en_revised', 75, 'The current budget is 75 euros.', True),
            ('en_revised', 75, '160 euros', False),
            ('en_revised', 75, '75 euros; previously 160 euros', False),
            ('de_present', 160, 'Betrag: 160 Euro', True),
            ('de_revised', 75, 'Betrag: 75 Euro\nWaehrung: 30 Euro', False),
            ('de_revised', 75, 'Betrag: 75 Euro', True),
        ):
            with self.subTest(name=name, answer=answer):
                self.assertEqual(bool(H.oracle_correct(name, answer, target)), expected)

    def test_absent_requires_exact_abstention(self):
        for name, correct in [('en_absent', 'UNKNOWN'), ('de_absent', 'UNBEKANNT')]:
            self.assertTrue(H.oracle_correct(name, correct, None))
            self.assertTrue(H.oracle_correct(name, correct + '.', None))
            for wrong in ('UNKREID', correct + ' but maybe 160 euros', '160 euros', ''):
                self.assertFalse(H.oracle_correct(name, wrong, None))

    def test_wrong_oracle_identity_fails_closed(self):
        with self.assertRaises(ValueError):
            H.oracle_correct('en_absent', '160 euros', 160)
        with self.assertRaises(ValueError):
            H.oracle_correct('en_present', 'UNKNOWN', None)
        with self.assertRaises(ValueError):
            H.oracle_correct('other', '160 euros', 160)

    def test_no_model_download_on_existing_scratch(self):
        with tempfile.TemporaryDirectory() as d:
            scratch = Path(d) / 'scratch'
            scratch.mkdir()
            with self.assertRaises(FileExistsError):
                H.run(scratch, Path(d) / 'evidence')


if __name__ == '__main__':
    unittest.main()
