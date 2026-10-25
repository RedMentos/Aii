"""Run316 fixed-cohort and resumable evidence harness (fixture-only tests)."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import native_c3_cohort_run316 as C
from v13.common import atomic_write, dumps


class NativeC3CohortRun316(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.out=Path(self.temp.name)/'cohort'

    def tearDown(self):self.temp.cleanup()

    def test_registry_is_immutable_disjoint_and_five_cases(self):
        self.assertEqual(C.registry_sha(),C.COHORT_SHA256)
        self.assertEqual(len(C.CASES),5)
        self.assertEqual(len({x['id'] for x in C.CASES}),5)
        self.assertEqual(len({x['code'] for x in C.CASES}),5)
        self.assertEqual(len({x['question'] for x in C.CASES}),5)
        self.assertNotIn('73194',{x['code'] for x in C.CASES})

    def test_fixture_only_five_real_sqlite_restart_and_forget_paths(self):
        result=C.run(self.out,native=False,timeout=20)
        self.assertEqual(result['status'],'COMPLETE')
        self.assertTrue(result['evidence_capture_pass'])
        self.assertEqual(result['metrics']['cases_attempted'],5)
        self.assertEqual(result['metrics']['utility_count'],5)
        self.assertEqual(result['metrics']['integration_count'],5)
        self.assertEqual(result['evidence_level'],'FIXTURE_ONLY')
        self.assertEqual(result['gates']['STEP2'],'UTILITY_FAIL')
        for case in C.CASES:
            raw=json.loads((self.out/('RUN316_'+case['id']+'.json')).read_text())
            self.assertFalse(raw['native'])
            self.assertEqual(raw['synthetic_correction'],case['code'])
            self.assertEqual([x['context']['contains_code'] for x in raw['stages']],[False,True,False])
            self.assertEqual([x['answer_contains_code'] for x in raw['stages']],[False,True,False])
        before={x['case_id']:x['raw_sha256'] for x in result['cases']}
        resumed=C.run(self.out,native=False,timeout=20)
        self.assertEqual(before,{x['case_id']:x['raw_sha256'] for x in resumed['cases']})
        self.assertEqual(len(resumed['cases']),5)

    def test_tampered_raw_case_blocks_resume(self):
        C.run(self.out,native=False,timeout=20)
        path=self.out/'RUN316_ASTER.json'
        path.write_text(path.read_text()+'\n')
        with self.assertRaisesRegex(ValueError,'raw case bytes changed'):
            C.run(self.out,native=False,timeout=20)

    def test_interrupted_third_case_preserves_two_and_resumes_remaining(self):
        original=C.one_probe
        calls=[0]
        def interrupt(*args,**kwargs):
            calls[0]+=1
            if calls[0]==3:raise KeyboardInterrupt('injected host interruption')
            return original(*args,**kwargs)
        with patch.object(C,'one_probe',side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt):C.run(self.out,native=False,timeout=20)
        partial=json.loads((self.out/'RUN316_COHORT.json').read_text())
        self.assertEqual(partial['status'],'PARTIAL')
        self.assertEqual(len(partial['cases']),2)
        preserved=[x['raw_sha256'] for x in partial['cases']]
        resumed=C.run(self.out,native=False,timeout=20)
        self.assertEqual(resumed['status'],'COMPLETE')
        self.assertEqual([x['raw_sha256'] for x in resumed['cases'][:2]],preserved)
        self.assertEqual(len(resumed['cases']),5)

    def test_utility_failure_is_counted_without_falsifying_integration(self):
        original=C.one_probe
        def weak_fixture(home,models_from,out,native,timeout):
            result=original(home,models_from,out,native=native,timeout=timeout)
            if C.P.QUESTION==C.CASES[1]['question']:
                result['utility_pass']=False
                result['utility']['second_exact']=False
                result['utility']['observed_improvement']=False
                atomic_write(out,(dumps(result)+'\n').encode())
            return result
        with patch.object(C,'one_probe',side_effect=weak_fixture):
            result=C.run(self.out,native=False,timeout=20)
        self.assertEqual(result['status'],'COMPLETE')
        self.assertTrue(result['evidence_capture_pass'])
        self.assertEqual(result['metrics']['integration_count'],5)
        self.assertEqual(result['metrics']['utility_count'],4)
        self.assertEqual(result['metrics']['utility_rate'],0.8)

    def test_modified_cohort_registry_is_refused(self):
        with patch.object(C,'COHORT_SHA256','not-the-frozen-hash'):
            with self.assertRaisesRegex(ValueError,'registry hash mismatch'):
                C.run(self.out,native=False)


if __name__=='__main__':unittest.main()
