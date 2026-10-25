"""Run315 harness regressions. Fixture is not native C3 evidence."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts import native_second_turn_probe_run315 as P


class NativeSecondTurnHarnessRun315(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.home=Path(self.temp.name)/'home'
        self.out=Path(self.temp.name)/'evidence.json'

    def tearDown(self):self.temp.cleanup()

    def test_fixture_only_correction_and_forget_through_real_runtime_sqlite(self):
        result=P.probe(self.home,None,self.out,native=False,timeout=20)
        self.assertEqual(result['status'],'COMPLETE')
        self.assertTrue(result['integration_pass'])
        self.assertTrue(result['utility_pass'])
        self.assertEqual(result['evidence_level'],'FIXTURE_ONLY')
        self.assertEqual([x['status'] for x in result['stages']],['FINAL']*3)
        self.assertEqual([x['answer_contains_code'] for x in result['stages']],[False,True,False])
        self.assertEqual([x['context']['contains_code'] for x in result['stages']],[False,True,False])
        self.assertEqual([x['recalled_code'] for x in result['stages']],[False,True,False])
        self.assertTrue(result['checks']['native_processes_reaped'])
        self.assertFalse(result['checks']['all_native_generated'])
        self.assertEqual(json.loads(self.out.read_text()),result)
        self.assertEqual(result['gates']['STEP2'],'UTILITY_FAIL')
        self.assertEqual(result['gates']['jepa_weight'],0)

    def test_native_missing_registered_source_fails_closed_and_persists_error(self):
        with self.assertRaisesRegex(ValueError,'requires pinned installed'):
            P.probe(self.home,None,self.out,native=True)
        result=json.loads(self.out.read_text())
        self.assertEqual(result['status'],'ERROR')
        self.assertEqual(result['error']['type'],'ValueError')
        self.assertEqual(result['stages'],[])
        self.assertTrue(result['native'])

    def test_wrong_native_model_hash_is_rejected_before_any_turn(self):
        self.home.mkdir(parents=True)
        fake=self.home/'wrong.gguf';fake.write_bytes(b'not the registered model')
        with patch.object(P,'attach_native_assets',return_value=None), \
             patch('v13.models.ModelManager',return_value=Mock(path_for=Mock(return_value=fake))):
            with self.assertRaisesRegex(ValueError,'model hash differs'):
                P.probe(self.home,self.home,self.out,native=True)
        result=json.loads(self.out.read_text())
        self.assertEqual(result['status'],'ERROR')
        self.assertEqual(result['stages'],[])
        self.assertNotEqual(result['model']['sha256'],result['model']['expected_sha256'])

    def test_interrupted_second_turn_retains_first_closed_checkpoint(self):
        original=P.stage
        calls=[0]
        def fail_second(*args,**kwargs):
            calls[0]+=1
            if calls[0]==2:raise RuntimeError('injected second stage failure')
            return original(*args,**kwargs)
        with patch.object(P,'stage',side_effect=fail_second):
            with self.assertRaisesRegex(RuntimeError,'second stage failure'):
                P.probe(self.home,None,self.out,native=False,timeout=20)
        result=json.loads(self.out.read_text())
        self.assertEqual(result['status'],'ERROR')
        self.assertEqual(len(result['stages']),1)
        self.assertEqual(result['stages'][0]['status'],'FINAL')
        self.assertEqual(result['error']['type'],'RuntimeError')

    def test_hash_helper_matches_actual_file_bytes(self):
        path=Path(self.temp.name)/'bytes.bin';path.write_bytes(b'run315\x00source')
        self.assertEqual(P.sha256_file(path),hashlib.sha256(path.read_bytes()).hexdigest())


if __name__=='__main__':unittest.main()
