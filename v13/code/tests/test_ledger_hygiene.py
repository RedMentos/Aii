"""WP-T15: every module has a completion-ledger row; blueprint knob bindings resolve; no module row claims PASS."""
from pathlib import Path
import tempfile
import unittest
from v13.runtime import Runtime
from v13.verification import completion_ledger,module_rows
from v13 import register

class LedgerHygiene(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name))
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def test_every_module_has_a_row_and_auto_rows_never_pass(self):
        led=completion_ledger(self.r);self.assertEqual(led['uncovered_modules'],[])
        auto=[x for x in led['rows'] if x.get('row_source')=='AUTO_MODULE_ROW'];self.assertTrue(auto)
        self.assertTrue(all(x['gate_status'] in ('PARTIAL','UNTESTED') for x in auto))
        ids=[x['feature_id'] for x in led['rows']];self.assertEqual(len(ids),len(set(ids)))
        row=next(x for x in auto if x['implementation_files']==['v13/authority.py'])
        self.assertIn('tests/test_authority.py',row['unit_tests']);self.assertIn('§88.1',row['canon_source'])
    def test_knob_bindings_resolve(self):
        s=register.summary();self.assertEqual(s['map_broken'],0);self.assertGreaterEqual(s['match']+s['documented_deviation'],92);self.assertEqual(s['drift'],0)
        e={x['id']:x for x in register.entries()}
        self.assertEqual(e['DREAM.fact_write_gain']['status'],'MATCH');self.assertEqual(e['B2.gist_span_min']['status'],'DOCUMENTED_DEVIATION');self.assertTrue(e['B2.gist_span_min']['deviation_reason'])

if __name__=='__main__':unittest.main()
