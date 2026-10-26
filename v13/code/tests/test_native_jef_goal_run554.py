"""Run554 fixture preflight only; native proof requires separate pinned runner/model CI."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.native_jef_goal_run554 import probe


class Run554Fixture(unittest.TestCase):
    def test_fixture_is_labeled_and_goal_operator_persists(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            out = root / 'fixture.json'
            report = probe(root / 'home', None, out, native=False, timeout=30)
            self.assertTrue(report['integration_pass'], report)
            self.assertEqual(report['status'], 'COMPLETE')
            self.assertEqual(report['evidence_level'], 'FIXTURE_ONLY')
            self.assertFalse(report['native'])
            self.assertFalse(report['checks']['native_generated'])
            self.assertTrue(report['checks']['own_final_receipt'])
            self.assertTrue(report['checks']['goal_done'])
            self.assertTrue(report['checks']['model_operator_refused'])
            self.assertTrue(report['checks']['restart_persisted'])
            self.assertEqual(json.loads(out.read_text())['status'], 'COMPLETE')

    def test_native_without_pinned_artifacts_fails_closed_and_saves_raw(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            out = root / 'missing.json'
            with self.assertRaisesRegex(ValueError, 'pinned public artifacts'):
                probe(root / 'home', None, out, native=True, timeout=2)
            report = json.loads(out.read_text())
            self.assertEqual(report['status'], 'ERROR')
            self.assertEqual(report['evidence_level'], 'LINUX_NATIVE_C3')
            self.assertFalse(report.get('integration_pass', False))


if __name__ == '__main__':
    unittest.main()
