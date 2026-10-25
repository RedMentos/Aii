"""Read-only native candidate source drift diagnostics, synthetic software tests."""
import tempfile
from pathlib import Path
import unittest

from scripts.native_candidate_drift_audit_20261025 import compare


class NativeCandidateDriftAudit(unittest.TestCase):
    def test_byte_exact_sources_are_only_source_match_not_native_proof(self):
        report, diff = compare({'v13/runtime.py':'a=1\n'}, {'v13/runtime.py':'a=1\n'})
        self.assertEqual(report['status'], 'BYTE_EXACT_MATCH')
        self.assertEqual(report['candidate_gate'], 'SOURCE_MATCH_ONLY_NOT_NATIVE_PROOF')
        self.assertEqual(diff, '')
        self.assertFalse(report['native_executed'])
        self.assertFalse(report['whole_system_complete'])

    def test_source_drift_is_fail_closed_and_complete_diff_is_preserved(self):
        expected = {'v13/runtime.py':'a=1\nb=2\n', 'v13/runners.py':'x=3\n'}
        actual = {'v13/runtime.py':'a=1\nb=4\n', 'v13/runners.py':'x=3\n'}
        report, diff = compare(expected, actual)
        self.assertEqual(report['status'], 'DRIFT_DETECTED')
        self.assertEqual(report['candidate_gate'], 'FAIL_SOURCE_DRIFT')
        self.assertFalse(report['source_paths']['v13/runtime.py']['byte_equal'])
        self.assertTrue(report['source_paths']['v13/runners.py']['byte_equal'])
        self.assertIn('-b=2', diff)
        self.assertIn('+b=4', diff)
        self.assertNotIn('x=3', diff)
        self.assertEqual(report['STEP2'], 'UTILITY_FAIL')
        self.assertEqual(report['jepa_weight'], 0)

    def test_file_set_mismatch_never_silently_succeeds(self):
        with self.assertRaises(ValueError):
            compare({'v13/runtime.py':'a'}, {'v13/store.py':'a'})


if __name__ == '__main__':
    unittest.main()
