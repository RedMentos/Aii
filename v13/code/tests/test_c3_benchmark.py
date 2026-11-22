import importlib.util
from pathlib import Path
import unittest
P=Path(__file__).resolve().parents[1]/'scripts/benchmark_c3.py'
spec=importlib.util.spec_from_file_location('benchmark_c3',P);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class C3Benchmark(unittest.TestCase):
    def test_lexical_smoke_checks_are_bounded(self):
        fx={'must_all':['120'],'must_any':['Budget','budget'],'forbid':['Cloud']}
        self.assertEqual(m.lexical_checks('Budget: 120 Euro.',fx),{'must_all':True,'must_any':True,'forbid':True})
        self.assertFalse(all(m.lexical_checks('Cloud budget unknown.',fx).values()))
    def test_fixture_set_includes_grounding_and_abstention(self):
        ids={x['id'] for x in m.FIXTURES}
        for lang in ('en','de'):self.assertIn(lang+'_grounded_report',ids);self.assertIn(lang+'_abstain',ids)
    def test_english_first_german_kept_as_transfer_test(self):
        self.assertEqual(m.FIXTURES[0]['lang'],'en');self.assertEqual({x['lang'] for x in m.FIXTURES},{'en','de'})
if __name__=='__main__':unittest.main()
