"""Software prereg controls for six fixed public C3 native bilingual probes.

Does not download models, execute a native binary, or score model semantics.
"""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import current_c3_native_bilingual_source_probe_20261029 as P
from scripts import current_c3_native_linux_smoke_20261028 as pinned


class C3NativeBilingualSourcePreregs(unittest.TestCase):
    def test_six_fixed_distinct_bilingual_conditions(self):
        names = [name for name, _ in P.CASES]
        self.assertEqual(names, [
            'en_present', 'en_absent', 'en_revised',
            'de_present', 'de_absent', 'de_revised',
        ])
        self.assertEqual(len(set(prompt for _, prompt in P.CASES)), 6)
        for name, prompt in P.CASES:
            with self.subTest(name=name):
                self.assertTrue(P._digest(prompt))
                if name.endswith('_absent'):
                    self.assertNotIn('120', prompt)
                    self.assertNotIn('90', prompt)
                    self.assertIn('UNKNOWN' if name.startswith('en_')
                                  else 'UNBEKANNT', prompt)
                elif name.endswith('_present'):
                    self.assertIn('120', prompt)
                    self.assertNotIn('90', prompt)
                else:
                    self.assertLess(prompt.index('120'), prompt.index('90'))

    def test_pinned_current_catalog_is_official_and_unchanged(self):
        meta, file, runner = pinned._catalog()
        self.assertEqual(meta['model_id'], 'LiquidAI/LFM2.5-350M-GGUF')
        self.assertEqual(meta['license_id'], 'LFM Open License 1.0')
        self.assertEqual(file['sha256'], pinned.MODEL_SHA)
        self.assertEqual(file['size'], pinned.MODEL_BYTES)
        self.assertEqual(runner['sha256'], pinned.RUNNER_SHA)
        self.assertEqual(runner['size'], pinned.RUNNER_BYTES)

    def test_explicit_no_authority_and_no_semantic_score(self):
        self.assertEqual(P.N_TOKENS, 48)
        self.assertEqual(P.N_CTX, 512)
        self.assertEqual(P.NEGATIVE_GATES['age0'], 'RECORD_ONLY')
        self.assertEqual(P.NEGATIVE_GATES['step2'], 'UTILITY_FAIL')
        self.assertEqual(P.NEGATIVE_GATES['b3_l1'], 'FAIL')
        self.assertEqual(P.NEGATIVE_GATES['jepa_weight'], 0)
        self.assertFalse(P.NEGATIVE_GATES['redmi_measured'])
        self.assertFalse(P.NEGATIVE_GATES['whole_system_complete'])

    def test_progress_replace_is_atomic_and_failure_keeps_previous(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'PROGRESS.json'
            P._write_atomic(path, {'rows': [1]})
            before = path.read_bytes()
            with mock.patch.object(P.os, 'replace', side_effect=OSError('test interruption')):
                with self.assertRaises(OSError):
                    P._write_atomic(path, {'rows': [1, 2]})
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(json.loads(path.read_text())['rows'], [1])
            self.assertFalse(list(Path(d).glob('.report-*')))

    def test_refuses_reuse_of_existing_native_scratch(self):
        with tempfile.TemporaryDirectory() as d:
            scratch = Path(d) / 'scratch'
            scratch.mkdir()
            with self.assertRaises(FileExistsError):
                P.run(scratch, Path(d) / 'fresh-evidence')

    def test_non_linux_refused_before_download(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(
            P.platform, 'system', return_value='Windows'
        ):
            with self.assertRaises(ValueError):
                P.run(Path(d) / 'scratch', Path(d) / 'evidence')


if __name__ == '__main__':
    unittest.main()
