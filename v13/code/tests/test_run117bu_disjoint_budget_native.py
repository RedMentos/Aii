"""Run117BU native paired harness synthetic software tests; no model executed."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run117bu_disjoint_budget_native as m

FIXTURE=Path(__file__).resolve().parents[1]/'docs/fixtures/RUN117BS_C3_DISJOINT_BUDGET_SEED1103.json'

class DisjointBudgetHarness(unittest.TestCase):
    def test_frozen_fixture(self):
        f=m.fixture(FIXTURE)
        self.assertEqual(f['seed'],1103)
        self.assertEqual(tuple(x['id'] for x in f['fixtures']),m.IDS)

    def test_frozen_fixture_mutation_denied(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'changed.json';p.write_bytes(FIXTURE.read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError,'FROZEN_FIXTURE_SHA_RED'):m.fixture(p)

    def test_counterbalanced_order(self):
        self.assertEqual(m.order(0),('TYPED_JEF','RAW_SOURCE'))
        self.assertEqual(m.order(1),('RAW_SOURCE','TYPED_JEF'))
        self.assertEqual(m.order(7),('RAW_SOURCE','TYPED_JEF'))

    def test_strict_semantic_scoring(self):
        oracle={'choice':'A','remaining':13}
        self.assertEqual(m.score('{"choice":"A","remaining":13}',oracle),
                         {'valid_json':True,'exact':True})
        for raw in ('{"choice":"A","remaining":true}',
                    '{"choice":"NONE","remaining":13}',
                    '{"choice":"A","remaining":NaN}',
                    '{"choice":"A","choice":"B","remaining":13}',
                    '{"choice":"A","remaining":13,"oracle":true}',
                    '{"choice":"A","remaining":-1}'):
            self.assertFalse(m.score(raw,oracle)['exact'])

    def fake(self,row,index,*,typed=True,raw=False):
        arms=[]
        for name in m.order(index):
            exact=typed if name=='TYPED_JEF' else raw
            arms.append({'arm':name,'status':'RECORDED','native_final':True,
                         'process_reaped':True,'source_rechecked':True,
                         'native_metrics':{'status':'FINAL'},
                         'score':{'valid_json':True,'exact':exact}})
        return {'id':row['id'],'status':'RECORDED','closed_store_ok':True,'arms':arms}

    def test_eight_stubbed_rows_do_not_prove_native(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'out'
            with patch.object(m,'pinned_c3',return_value={'synthetic':'stub'}),\
                 patch.object(m,'run_row',side_effect=lambda home,inst,row,i:self.fake(row,i)) as run:
                result=m.run(Path(d)/'installed',out,FIXTURE)
            self.assertEqual(run.call_count,8)
            self.assertEqual(result['summary']['scores'],{'TYPED_JEF':8,'RAW_SOURCE':0})
            self.assertEqual(result['summary']['paired_net'],8)
            self.assertEqual(result['status'],'EXPLORATORY_TYPED_ADVANTAGE')
            self.assertFalse(result['independent_generalization'])
            self.assertEqual(result['jepa_weight'],0)
            self.assertEqual(result['native_body_calls'],0)

    def test_failed_row_or_raw_tie_denies_signal(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(m,'pinned_c3',return_value={'synthetic':'stub'}),\
                 patch.object(m,'run_row',side_effect=lambda home,inst,row,i:self.fake(row,i,typed=True,raw=True)):
                result=m.run(Path(d)/'installed',Path(d)/'out',FIXTURE)
            self.assertEqual(result['status'],'NO_EXPLORATORY_TYPED_ADVANTAGE')
            self.assertEqual(result['summary']['paired_net'],0)

    def test_existing_output_denied(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'out';out.mkdir()
            with self.assertRaises(FileExistsError):m.run(Path(d)/'installed',out,FIXTURE)

if __name__=='__main__':unittest.main()
