"""Run445 negative controls and exact actual native210 replay."""
import json
import os
import stat
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path

import run442_native_seed_variance as base
import run445_native210_p21_source_audit as audit


class Run445Native210Audit(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.archive = Path(self.temp.name) / 'native210.zip'

    def test_outer_sha_mismatch(self):
        with zipfile.ZipFile(self.archive, 'w') as z:
            z.writestr(base.MANIFEST, '{}')
        with self.assertRaisesRegex(ValueError, 'OUTER_SHA_MISMATCH'):
            audit.analyze(self.archive, '0' * 64)

    def test_duplicate_zip_rejected(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(self.archive, 'w') as z:
                z.writestr(base.MANIFEST, '{}')
                z.writestr(base.MANIFEST, '{}')
        with self.assertRaisesRegex(ValueError, 'ZIP_DUPLICATE_OR_MISSING_MANIFEST'):
            audit.analyze(self.archive, base.sha(self.archive.read_bytes()))

    def test_inner_hash_rejected(self):
        manifest = {'schema': 'RUN409_SAFE_NATIVE_EXPORT_V1',
                    'canonical_gate_pass': False, 'step2_exit': 'UTILITY_FAIL',
                    'copied': {'report.dat': {'bytes': 4, 'sha256': '0'*64}}}
        with zipfile.ZipFile(self.archive, 'w') as z:
            z.writestr(base.MANIFEST, json.dumps(manifest))
            z.writestr('report.dat', b'data')
        with self.assertRaisesRegex(ValueError, 'INNER_SHA_MISMATCH'):
            audit.analyze(self.archive, base.sha(self.archive.read_bytes()))

    def test_zip_symlink_rejected(self):
        link = zipfile.ZipInfo('external.dat')
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        with zipfile.ZipFile(self.archive, 'w') as z:
            z.writestr(base.MANIFEST, '{}')
            z.writestr(link, b'/outside')
        with self.assertRaisesRegex(ValueError, 'ZIP_SPECIAL_FILE'):
            audit.analyze(self.archive, base.sha(self.archive.read_bytes()))

    def test_actual_210_row_source_identity_no_causal_promotion(self):
        path = os.environ.get('RUN445_ARCHIVE')
        if not path:
            self.skipTest('Pinned Run437 safe no-model artifact required')
        result = audit.analyze(path)
        self.assertEqual(result['verified_files'], 147)
        self.assertEqual(result['source_tool_replay_verified'], 210)
        self.assertFalse(result['canonical_gate_pass'])
        self.assertEqual(result['step2_exit'], 'UTILITY_FAIL')
        p = result['pairs']['P_s21_minus_O_s21']
        self.assertEqual(p['both_exact']['mean_utility_delta'], 0.194444444445)
        self.assertEqual(p['both_exact']['same_inputs'], 1)
        self.assertEqual(p['both_exact']['same_b1_offers'], 2)
        self.assertEqual(p['both_exact']['same_b2_offers'], 2)
        self.assertEqual(p['b1_only']['mean_utility_delta'], 0)
        self.assertEqual(p['same_policy_dual']['same_answers'], 6)


if __name__ == '__main__':
    unittest.main()
