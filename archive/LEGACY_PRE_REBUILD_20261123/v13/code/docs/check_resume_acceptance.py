"""Synthetic integrity-guard fixtures only: no native inference or phone proof."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

MODULE=Path(__file__).with_name('resume_acceptance.py')
spec=importlib.util.spec_from_file_location('resume_acceptance',MODULE);resume=importlib.util.module_from_spec(spec);spec.loader.exec_module(resume)

class ResumeGuards(unittest.TestCase):
    def fixture(self,td,completed=('jef-modes','experience'),remaining='learning'):
        app=Path(td)/'app';out=Path(td)/'moved';app.mkdir();out.mkdir()
        for folder in ('v13','scripts','tests','specs'):(app/folder).mkdir()
        (app/'v13/example.py').write_text('synthetic_fixture=1\n')
        # Registry uses the actual pinned collector file; placeholder stage files
        # exist for AST guards only and are never executed by these tests.
        (app/'scripts/acceptance.py').write_bytes((resume.APP/'scripts/acceptance.py').read_bytes())
        for p in list((resume.APP/'tests').glob('integration_*.py'))+list((resume.APP/'scripts').glob('benchmark_c3.py')):
            target=app/p.relative_to(resume.APP);target.write_text('# synthetic no native calls\n')
        (app/'specs/pins.json').write_text('{"fixture":true}')
        source={'v13/example.py':resume.file_hash(app/'v13/example.py')};dev={'platform':'SYNTHETIC','machine':'fixture','python':'0','android':False,'cpu_count':1}
        report={'status':'RUNNING','device':dev,'source_hashes':source,'harness_hashes':resume.verifier.harness_hashes(app),'canonical_architecture_complete':False,'stages':[]}
        for name in completed:
            expected=resume.verifier.STATUSES[name];data={'proof_status':expected} if name=='learning' else {'all_passed':expected} if name=='cancel-restart' else {'status':expected};data['source_hashes']=source;data['device']=dev;data['synthetic_fixture_only']=True
            if name in ('memory-retrieval','output-adapter'):
                feature=out/(name+'.features.json.gz');feature.write_bytes(b'SYNTHETIC guard fixture, not model states')
                data['native_feature_artifact' if name=='memory-retrieval' else 'feature_artifact']={'sha256':resume.file_hash(feature)}
            artifact=out/(name+'.json');artifact.write_text(json.dumps(data));(out/(name+'.log')).write_text('synthetic guard fixture only\n')
            report['stages'].append({'name':name,'status':'PASS','exit_code':0,'observed_status':expected,'artifact':'/lost/original/'+name+'.json','artifact_sha256':resume.file_hash(artifact),'log':'/lost/original/'+name+'.log'})
        if remaining:
            (out/(remaining+'.json')).write_text('{"status":"RUNNING","synthetic_fixture_only":true}');(out/(remaining+'.log')).write_text('unfinished fixture\n');report['stages'].append({'name':remaining,'status':'RUNNING'})
        report['stages'].sort(key=lambda r:list(resume.verifier.STATUSES).index(r['name']))
        path=out/'acceptance.json';path.write_text(json.dumps(report));return app,path,report,dev
    def check(self,app,path,dev,**kwargs):return resume.validate_report(path,app,False,True,dev,kwargs.get('identity'))
    def test_registry_matches_exact_actual_cli_and_21_stage_order(self):
        plan=resume.registry(resume.APP,False,True);self.assertEqual(len(plan),21)
        by={s['name']:s for s in plan};self.assertEqual(by['sustained']['extra_args'],['--cycles','12']);self.assertEqual(by['output-adapter']['extra_args'],['--production']);self.assertEqual(by['predictor-b2']['extra_args'],['--role','B2_GIST']);self.assertEqual(by['c3-comparison']['extra_args'],['--download-candidate'])
        self.assertEqual(len(resume.registry(resume.APP,True,False)),16)
    def test_relocated_completed_siblings_preserved_and_unfinished_is_remaining(self):
        with tempfile.TemporaryDirectory() as td:
            app,path,j,d=self.fixture(td);before={p.name:resume.file_hash(p) for p in path.parent.iterdir()};_,plan,passed=self.check(app,path,d)
            self.assertEqual(passed,['jef-modes','experience']);self.assertEqual(len(plan),21);self.assertEqual(before,{p.name:resume.file_hash(p) for p in path.parent.iterdir()})
    def test_changed_source_harness_device_refused(self):
        for kind in ('source','harness','device'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as td:
                app,path,j,d=self.fixture(td)
                if kind=='source':(app/'v13/example.py').write_text('changed=2\n')
                elif kind=='harness':(app/'specs/pins.json').write_text('{}')
                else:d=d|{'android':True}
                with self.assertRaises(resume.GuardError):self.check(app,path,d)
    def test_completed_artifact_or_status_or_log_not_silently_retried(self):
        for kind in ('hash','status','exit','log'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as td:
                app,path,j,d=self.fixture(td)
                if kind=='hash':(path.parent/'experience.json').write_text('{}')
                elif kind=='status':
                    p=path.parent/'experience.json';p.write_text('{"status":"FAIL"}');j['stages'][1]['artifact_sha256']=resume.file_hash(p)
                elif kind=='exit':j['stages'][1]['exit_code']=2
                else:(path.parent/'experience.log').unlink()
                path.write_text(json.dumps(j))
                with self.assertRaises(resume.GuardError):self.check(app,path,d)
    def test_both_actual_feature_companion_hashes_required(self):
        for name in ('memory-retrieval','output-adapter'):
            with self.subTest(name=name),tempfile.TemporaryDirectory() as td:
                app,path,j,d=self.fixture(td,completed=(name,),remaining=None);self.check(app,path,d)
                (path.parent/(name+'.features.json.gz')).write_bytes(b'changed')
                with self.assertRaisesRegex(resume.GuardError,'features'):self.check(app,path,d)
    def test_unknown_duplicate_and_false_complete_refused(self):
        for kind in ('unknown','duplicate','complete'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as td:
                app,path,j,d=self.fixture(td)
                if kind=='unknown':j['stages'].append({'name':'made-up','status':'PASS'})
                elif kind=='duplicate':j['stages'].append(j['stages'][0])
                else:j['status']='IMPLEMENTED_PATHS_PASS'
                path.write_text(json.dumps(j))
                with self.assertRaises(resume.GuardError):self.check(app,path,d)
    def test_failed_attempt_archived_with_hashes_and_passes_untouched(self):
        with tempfile.TemporaryDirectory() as td:
            app,path,j,d=self.fixture(td);before=resume.file_hash(path.parent/'experience.json');row=j['stages'][-1]
            target=resume.archive_attempt(path.parent,'learning','fixture-segment',row)
            self.assertEqual(resume.file_hash(path.parent/'experience.json'),before);self.assertFalse((path.parent/'learning.json').exists())
            manifest=json.loads((target/'attempt-manifest.json').read_text());self.assertEqual(manifest['learning.json'],resume.file_hash(target/'learning.json'))
            with self.assertRaises(FileExistsError):resume.archive_attempt(path.parent,'learning','fixture-segment',row)
    def test_resume_modes_identity_and_attested_log_hash_guard(self):
        for kind in ('mode','identity','log'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as td:
                app,path,j,d=self.fixture(td);identity={'kind':'SYNTHETIC','sha256':'a'*64};j['resume_provenance']={'options':{'quick':False,'compare_c3':True},'stable_identity':identity,'preserved_pass_logs':[{'file':'experience.log','sha256':resume.file_hash(path.parent/'experience.log')}]}
                if kind=='mode':j['resume_provenance']['options']['quick']=True
                elif kind=='identity':identity=identity|{'sha256':'b'*64}
                else:(path.parent/'experience.log').write_text('changed')
                path.write_text(json.dumps(j))
                with self.assertRaises(resume.GuardError):self.check(app,path,d,identity=identity)
    def test_incremental_mirror_includes_failed_attempt_and_existing_pass_features(self):
        with tempfile.TemporaryDirectory() as td:
            app,path,j,d=self.fixture(td,completed=('output-adapter',),remaining='a3-student');archive=Path(td)/'archive';resume.archive_attempt(path.parent,'a3-student','fixture-segment',j['stages'][-1]);resume.mirror(path.parent,archive)
            for p in path.parent.rglob('*'):
                if p.is_file():self.assertEqual(resume.file_hash(p),resume.file_hash(archive/p.relative_to(path.parent)))

if __name__=='__main__':unittest.main(verbosity=2)
