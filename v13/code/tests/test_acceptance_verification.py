"""Proof-integrity tests with synthetic reports, never native-output claims."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('acceptance_verifier',Path(__file__).resolve().parents[1]/'scripts/verify_acceptance.py')
verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)

class ProofIntegrity(unittest.TestCase):
    def fixture(self,folder):
        app=Path(folder);(app/'v13').mkdir();(app/'v13/example.py').write_text('fixture=1\n')
        (app/'specs').mkdir();(app/'specs/pins.json').write_text('{"fixture":1}')
        source={'v13/example.py':verifier.sha(app/'v13/example.py')};report={'status':'IMPLEMENTED_PATHS_PASS','source_hashes':source,'harness_hashes':verifier.harness_hashes(app),'stages':[]}
        for name,status in verifier.STATUSES.items():
            data={'proof_status':status} if name=='learning' else {'all_passed':status} if name=='cancel-restart' else {'status':status}
            if name in {'memory-retrieval','output-adapter'}:
                features=app/(name+'.features.json.gz');features.write_bytes(b'synthetic integrity fixture only')
                data['native_feature_artifact' if name=='memory-retrieval' else 'feature_artifact']={'sha256':verifier.sha(features)}
            data['source_hashes']=source;artifact=app/(name+'.json');artifact.write_text(json.dumps(data))
            report['stages'].append({'name':name,'status':'PASS','exit_code':0,'observed_status':status,'artifact':'/lost/workspace/'+name+'.json','artifact_sha256':verifier.sha(artifact)})
        path=app/'acceptance.json';path.write_text(json.dumps(report));return app,path,report
    def test_sibling_artifacts_verify_after_original_workspace_lost(self):
        with tempfile.TemporaryDirectory() as td:
            app,path,_=self.fixture(td);self.assertEqual(verifier.verify(path,app,compare_c3=True)['status'],'PASS')
    def test_running_and_missing_or_duplicate_stages_never_pass(self):
        with tempfile.TemporaryDirectory() as td:
            app,path,j=self.fixture(td)
            for status,rows in [('RUNNING',j['stages']),('IMPLEMENTED_PATHS_PASS',j['stages'][:-1]),('IMPLEMENTED_PATHS_PASS',j['stages']+[j['stages'][0]])]:
                path.write_text(json.dumps(j|{'status':status,'stages':rows}));self.assertEqual(verifier.verify(path,app,compare_c3=True)['status'],'FAIL')
    def test_changed_source_and_artifact_cannot_be_relabelled_current(self):
        with tempfile.TemporaryDirectory() as td:
            app,path,_=self.fixture(td);(app/'v13/example.py').write_text('changed=2\n');self.assertEqual(verifier.verify(path,app,compare_c3=True)['status'],'FAIL')
        with tempfile.TemporaryDirectory() as td:
            app,path,_=self.fixture(td);(app/'readouts.json').write_text('{}');self.assertEqual(verifier.verify(path,app,compare_c3=True)['status'],'FAIL')
    def test_failed_artifact_status_is_rejected_even_when_hash_updated(self):
        with tempfile.TemporaryDirectory() as td:
            app,path,j=self.fixture(td);artifact=app/'readouts.json';artifact.write_text(json.dumps({'status':'READOUT_PARTIAL'}))
            next(r for r in j['stages'] if r['name']=='readouts')['artifact_sha256']=verifier.sha(artifact);path.write_text(json.dumps(j))
            self.assertEqual(verifier.verify(path,app,compare_c3=True)['status'],'FAIL')
    def test_changed_specification_requires_a_new_collector_run(self):
        with tempfile.TemporaryDirectory() as td:
            app,path,_=self.fixture(td);(app/'specs/pins.json').write_text('{"fixture":2}');r=verifier.verify(path,app,compare_c3=True)
            self.assertEqual(r['status'],'FAIL');self.assertTrue(r['source_hashes_match']);self.assertFalse(r['harness_hashes_match'])
    def test_quick_coverage_must_be_requested_explicitly(self):
        with tempfile.TemporaryDirectory() as td:
            app,path,j=self.fixture(td);j['stages']=[r for r in j['stages'] if r['name'] not in verifier.FULL_ONLY|{'c3-comparison'}];path.write_text(json.dumps(j))
            self.assertEqual(verifier.verify(path,app)['status'],'FAIL');self.assertEqual(verifier.verify(path,app,quick=True)['status'],'PASS')
    def test_changed_native_memory_features_cannot_pass(self):
        with tempfile.TemporaryDirectory() as td:
            app,path,_=self.fixture(td);(app/'memory-retrieval.features.json.gz').write_bytes(b'changed')
            self.assertEqual(verifier.verify(path,app,compare_c3=True)['status'],'FAIL')
    def test_changed_native_output_features_cannot_pass(self):
        with tempfile.TemporaryDirectory() as td:
            app,path,_=self.fixture(td);(app/'output-adapter.features.json.gz').write_bytes(b'changed')
            self.assertEqual(verifier.verify(path,app,compare_c3=True)['status'],'FAIL')
