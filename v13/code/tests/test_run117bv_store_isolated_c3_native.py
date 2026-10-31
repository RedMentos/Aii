"""Run117BV: real Store with mocked native process, no Runtime background worker."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run117bp_jef_c3_budget_native_smoke as s

FIXTURE=Path(__file__).resolve().parents[1]/'docs/fixtures/run46b_jef_source_eligibility_seed401.json'

class FakeRunner:
    def __init__(self):self.last_metrics={}
    def generate(self,messages,cancel,deadline,max_tokens,schema,seed=None):
        packet=json.loads(messages[1]['content'])
        self.last_metrics={'status':'FINAL','actual_model':'MOCK_NOT_NATIVE'}
        yield json.dumps(packet['typed_jef_candidate'])

class FakePool:
    def __init__(self,*args,**kwargs):
        self.runner=FakeRunner();self.release_history=[]
    def get(self,role):
        assert role=='C3_LANGUAGE'
        return self.runner
    def unload(self):
        if not self.release_history:
            self.release_history.append({'role':'C3_LANGUAGE','before':{'pid':123},'process_reaped':True})

class IsolatedStore(unittest.TestCase):
    def test_six_real_store_sources_rechecked_without_runtime_worker(self):
        f=s.fixture(FIXTURE)
        with tempfile.TemporaryDirectory() as t:
            with patch.object(s,'installed_links',return_value=None),\
                 patch.object(s,'ModelManager',return_value=object()),\
                 patch.object(s,'RunnerPool',FakePool):
                for row in f['fixtures']:
                    result=s.run_row(Path(t)/row['id'],Path(t)/'installed',row)
                    with self.subTest(id=row['id']):
                        self.assertEqual(result['status'],'RECORDED',result)
                        self.assertEqual(result['guard']['status'],'FORMATTER_MATCH_SHADOW')
                        self.assertTrue(result['guard']['source_rechecked'])
                        self.assertTrue(result['process_reaped'])
                        self.assertTrue(result['closed_store_ok'])
                        self.assertTrue(result['native_final'])
                        self.assertEqual(result['native_c3_metrics']['actual_model'],'MOCK_NOT_NATIVE')

if __name__=='__main__':unittest.main()
