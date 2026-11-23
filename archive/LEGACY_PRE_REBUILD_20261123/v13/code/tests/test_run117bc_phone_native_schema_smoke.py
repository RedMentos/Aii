"""Run117BC extracted phone ZIP software-only and strict native preflight controls."""
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from scripts import install_selftest_run117bc as bc
from scripts import package_source

class Run117BCPhone(unittest.TestCase):
    def test_frozen_three_new_validation_rows(self):
        r=bc.rows()
        self.assertEqual(tuple(x['id'] for x in r),bc.IDS)
        self.assertEqual(tuple(x['oracle_action'] for x in r),bc.ACTIONS)

    def test_missing_zip_is_red_no_native(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            self.assertFalse(bc.outer(root/'missing.zip',root/'work',root/'raw',None))
            r=json.loads((root/'raw/report.json').read_text())
            self.assertEqual(r['status'],'STRUCTURAL_RED_NO_PROMOTION')
            self.assertFalse(r['native_requested'])
            self.assertNotIn('native_c3_calls',r)

    def test_native_missing_binding_red_without_call(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            self.assertFalse(bc.worker(root/'work',root/'raw',root/'missing',native=True))
            r=json.loads((root/'raw/report.json').read_text())
            self.assertEqual(r['native_c3_calls'],0)
            self.assertEqual(r['status'],'STRUCTURAL_RED_NO_PROMOTION')

    def test_software_worker_three_real_source_bound_drafts(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            self.assertTrue(bc.worker(root/'work',root/'raw',None))
            r=json.loads((root/'raw/report.json').read_text())
            self.assertEqual(r['strict_formatter_exact_count'],3)
            self.assertEqual(r['native_c3_calls'],0)
            for x in r['rows']:
                self.assertEqual(x['store_audit']['action_kinds'],['TEXT_REPORT'])
                self.assertEqual(x['store_audit']['live_output_count'],0)

    def test_zip_crc_tamper_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'bad.zip'
            with zipfile.ZipFile(p,'w') as z:z.writestr('fake','text')
            self.assertFalse(bc.outer(p,root/'work',root/'raw',None))
            r=json.loads((root/'raw/report.json').read_text())
            self.assertEqual(r['status'],'STRUCTURAL_RED_NO_PROMOTION')
            self.assertEqual(r['error_type'],'KeyError')

if __name__=='__main__':unittest.main()
