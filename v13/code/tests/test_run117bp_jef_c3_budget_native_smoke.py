"""Run117BP known-cohort native harness software tests (no model invoked)."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run117bp_jef_c3_budget_native_smoke as s

FIXTURE=Path(__file__).resolve().parents[1]/'docs/fixtures/run46b_jef_source_eligibility_seed401.json'


class BudgetNativeHarness(unittest.TestCase):
    def test_frozen_known_cohort(self):
        f=s.fixture(FIXTURE)
        self.assertEqual(f['seed'],401)
        self.assertEqual(tuple(x['id'] for x in f['fixtures']),s.FIXTURE_IDS)
        self.assertEqual(s.sha(FIXTURE.read_bytes()),s.FIXTURE_SHA)

    def test_modified_fixture_never_reuses_frozen_label(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'fixture.json'
            p.write_bytes(FIXTURE.read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError,'FROZEN_FIXTURE_SHA_RED'):
                s.fixture(p)

    def test_summary_requires_actual_final_and_reap(self):
        rows=[{'status':'RECORDED','native_final':True,'process_reaped':True,
               'guard':{'source_rechecked':True}},
              {'status':'FORMATTER_OR_NATIVE_RED','native_final':True,
               'process_reaped':False,'guard':{'source_rechecked':True}}]
        self.assertEqual(s.summary(rows),{'rows':2,'native_final':2,'process_reaped':1,
                                          'source_rechecked':2,'formatter_match':1})

    def fake(self,row,*,match=True):
        return {'id':row['id'],'status':'RECORDED' if match else 'FORMATTER_OR_NATIVE_RED',
                'native_final':True,'process_reaped':True,
                'guard':{'status':'FORMATTER_MATCH_SHADOW' if match else 'FORMATTER_MISMATCH_RED',
                         'source_rechecked':True},
                'native_c3_metrics':{'status':'FINAL'}}

    def test_six_model_free_stubbed_rows_not_native_proof(self):
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)/'out'
            with patch.object(s,'installed_artifacts',return_value={'synthetic':'not native'}),\
                 patch.object(s,'run_row',side_effect=lambda h,i,row:self.fake(row)) as stub:
                r=s.run(Path(t)/'fake-installed',out,FIXTURE)
            self.assertEqual(stub.call_count,6)
            self.assertEqual(r['status'],'NATIVE_FORMATTER_SMOKE_MATCH_6_OF_6')
            self.assertEqual(r['summary']['formatter_match'],6)
            self.assertEqual(r['native_c3_calls'],6)
            self.assertTrue(r['registered_cohort_reused'])
            self.assertFalse(r['independent_generalization'])
            self.assertEqual(r['learning_authority'],0)
            self.assertEqual(r['jepa_weight'],0)
            self.assertEqual(json.loads((out/'report.json').read_text())['status'],r['status'])

    def test_one_failed_row_keeps_failure_and_denies_signal(self):
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)/'out'
            with patch.object(s,'installed_artifacts',return_value={'synthetic':'not native'}),\
                 patch.object(s,'run_row',side_effect=lambda h,i,row:self.fake(row,match=row['id']!='Orion')):
                r=s.run(Path(t)/'fake-installed',out,FIXTURE)
            self.assertEqual(r['status'],'NATIVE_FORMATTER_SMOKE_NO_FULL_SIGNAL')
            self.assertEqual(r['summary']['formatter_match'],5)
            self.assertEqual(len(r['row_sha256']),6)

    def test_existing_output_never_overwritten(self):
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)/'out';out.mkdir()
            with self.assertRaises(FileExistsError):s.run(Path(t)/'fake-installed',out,FIXTURE)


if __name__=='__main__':unittest.main()
