"""Run442 synthetic negatives and exact real native source-only replay."""
import json
import os
import stat
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path

import run442_native_seed_variance as m


class Run442SourceAuditTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.path = Path(self.t.name) / 'artifact.zip'

    def test_outer_hash_mismatch_rejected(self):
        with zipfile.ZipFile(self.path, 'w') as z:
            z.writestr(m.MANIFEST, '{}')
        with self.assertRaisesRegex(ValueError, 'OUTER_SHA_MISMATCH'):
            m.analyze(self.path, '0' * 64)

    def test_duplicate_zip_member_rejected(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(self.path, 'w') as z:
                z.writestr(m.MANIFEST, '{}')
                z.writestr(m.MANIFEST, '{}')
        with self.assertRaisesRegex(ValueError, 'ZIP_DUPLICATE_OR_MISSING_MANIFEST'):
            m.analyze(self.path, m.sha(self.path.read_bytes()))

    def test_wrong_inner_hash_rejected(self):
        manifest = {'schema': 'RUN409_SAFE_NATIVE_EXPORT_V1',
                    'canonical_gate_pass': False, 'step2_exit': 'UTILITY_FAIL',
                    'copied': {'report.dat': {'bytes': 4, 'sha256': '0'*64}}}
        with zipfile.ZipFile(self.path, 'w') as z:
            z.writestr(m.MANIFEST, json.dumps(manifest))
            z.writestr('report.dat', b'data')
        with self.assertRaisesRegex(ValueError, 'INNER_SHA_MISMATCH'):
            m.analyze(self.path, m.sha(self.path.read_bytes()))

    def test_symlink_member_rejected(self):
        symlink = zipfile.ZipInfo('link.dat')
        symlink.create_system = 3
        symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
        with zipfile.ZipFile(self.path, 'w') as z:
            z.writestr(m.MANIFEST, '{}')
            z.writestr(symlink, b'/outside')
        with self.assertRaisesRegex(ValueError, 'ZIP_SPECIAL_FILE'):
            m.analyze(self.path, m.sha(self.path.read_bytes()))

    def test_mixed_case_model_path_rejected(self):
        for path in ('Models/renamed.dat', 'attempts/O_s20/MoDeLs/opaque.bin'):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'UNSAFE_ARCHIVE_PATH'):
                m.safe(path)

    def test_actual_native168_observational_diagnostic(self):
        archive = os.environ.get('RUN442_ARCHIVE')
        if not archive:
            self.skipTest('Exact pinned artifact not available in this source-only context')
        result = m.analyze(archive)
        self.assertEqual(result['copied_files_verified'], 131)
        self.assertEqual(result['rows_compared'], 84)
        self.assertFalse(result['canonical_gate_pass'])
        self.assertEqual(result['step2_exit'], 'UTILITY_FAIL')
        self.assertEqual(result['pairs']['both_exact']['same_inputs'], 0)
        self.assertEqual(result['pairs']['same_policy_dual']['same_answers'], 6)
        self.assertEqual(result['pairs']['both_exact']['mean_delta_seed21_minus20'], -0.138888888889)


if __name__ == '__main__':
    unittest.main()
