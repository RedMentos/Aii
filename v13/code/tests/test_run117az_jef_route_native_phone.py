"""Run117AZ six-case JEF route native script model-free guard tests."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run117az_jef_route_native_phone as az


class Run117AZNativeRoute(unittest.TestCase):
    def test_six_frozen_reused_calibration_ids_and_hash(self):
        r = az.rows()
        self.assertEqual(tuple(x['id'] for x in r), az.IDS)
        self.assertEqual(tuple(x['oracle_action'] for x in r), az.ACTIONS)
        self.assertEqual(len({x['id'] for x in r}), 6)
        self.assertEqual(len({x['current'] for x in r}), 6)

    def test_frozen_cohort_rejects_change(self):
        r = az.p2x.fixtures()
        for row in r:
            if row['id'] == az.IDS[0]:
                row['current'] += ' forged'
        with patch.object(az.p2x, 'fixtures', return_value=r):
            with self.assertRaises((ValueError, AssertionError)):
                az.rows()

    def test_real_six_source_bound_drafts_without_native(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertTrue(az.run(root/'work', None, root/'raw', native=False))
            report = json.loads((root/'raw/report.json').read_text())
            self.assertEqual(report['status'], 'STRUCTURAL_GREEN_NO_PROMOTION')
            self.assertEqual(report['native_c3_calls'], 0)
            self.assertEqual(report['formatter_exact_count'], 6)
            self.assertEqual(len(report['rows']), 6)
            for item in report['rows']:
                self.assertEqual(item['cli']['status'], 'SHADOW_DRAFT_PREFLIGHT_READY')
                self.assertEqual(item['store_audit']['action_kinds'], ['TEXT_REPORT'])
                self.assertEqual(item['store_audit']['live_output_count'], 0)
                self.assertEqual(item['store_audit']['assistant_messages'], 1)
                self.assertEqual(item['cli']['delivery_authority'], 0)
                self.assertNotIn('policy_source', item['cli'])
                self.assertNotIn('sheet_source', item['cli'])
                self.assertNotIn('current', item['cli'])

    def test_no_installed_native_binding_is_red_before_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertFalse(az.run(root/'work', root/'missing', root/'raw', native=True))
            r = json.loads((root/'raw/report.json').read_text())
            self.assertEqual(r['status'], 'STRUCTURAL_RED_NO_PROMOTION')
            self.assertEqual(r['native_c3_calls'], 0)
            self.assertEqual(r['rows'], [])

    def test_nonempty_work_or_existing_out_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'out').mkdir()
            with self.assertRaises(FileExistsError):
                az.run(root/'work', None, root/'out')
            (root/'work').mkdir()
            (root/'work'/'sentinel').write_text('no overwrite')
            with self.assertRaises(FileExistsError):
                az.run(root/'work', None, root/'other')


if __name__ == '__main__':
    unittest.main()
