"""SOFTWARE guards only; no native-model inference or approval evidence."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch,MagicMock
from v13.common import dumps,file_hash
from v13.config import DEFAULTS

spec=importlib.util.spec_from_file_location('causal_diagnostic',Path(__file__).with_name('integration_causal_output_lifecycle.py'))
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)

class CollectorGuards(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.installed=self.root/'installed';self.out=self.root/'attempt'
        (self.installed/'config').mkdir(parents=True);(self.installed/'bin').mkdir();self.worker=self.installed/'bin/stream';self.worker.write_bytes(b'SOFTWARE_WORKER_NO_NATIVE')
        for name in ('runner.json','native-prefill-stream.json'):c.write(self.installed/'config'/name,{'fixture':'SOFTWARE'})
        c.write(self.installed/'config/settings.json',DEFAULTS);c.write(self.installed/'config/models.json',{'fixture':{'files':{}}})
        self.binding={'binary':str(self.worker),'binary_sha256':file_hash(self.worker),'feature_abi':{'test_only':True},'identity':{'fixture':'SOFTWARE_NO_NATIVE'}}
        self.bound=patch.object(c,'check_prepared',return_value=self.binding);self.bound.start()
    def tearDown(self):self.bound.stop();self.temp.cleanup()
    def prepare(self):return c.prepare(self.installed,self.out)

    def test_fixed_earliest46_partition_preserves_original_source_folds(self):
        rows=c.fixture();self.assertEqual(len(rows),46)
        for condition,expected in [(lambda f:f>=2,(25,[11,14])),(lambda f:f==1,(13,[7,6])),(lambda f:f==0,(8,[5,3]))]:
            chosen=[r for r in rows if condition(r['fold'])];self.assertEqual((len(chosen),[sum(r['target_class']==t for r in chosen) for t in (0,1)]),expected)
        with patch.object(c,'file_hash',return_value='foreign'):
            with self.assertRaisesRegex(ValueError,'corpus changed'):c.fixture()

    def test_prepare_read_only_and_resolved_worker_alias(self):
        before={p.name:p.read_bytes() for p in (self.installed/'config').iterdir()}
        with patch.object(c,'Runtime',side_effect=AssertionError('Native Runtime forbidden')):
            manifest=self.prepare();c.verify(self.out)
        self.assertEqual(before,{p.name:p.read_bytes() for p in (self.installed/'config').iterdir()})
        alias=self.root/'alias';alias.symlink_to(self.worker)
        self.assertEqual(c.canonical_binding({**self.binding,'binary':str(alias)}),manifest['binding'])
        alien=self.root/'alien';alien.write_bytes(self.worker.read_bytes())
        self.assertNotEqual(c.canonical_binding({**self.binding,'binary':str(alien)}),manifest['binding'])

    def test_prepare_cannot_overwrite_existing_evidence(self):
        self.prepare();before=(self.out/'manifest.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'Fresh'):self.prepare()
        self.assertEqual(before,(self.out/'manifest.json').read_bytes())

    def test_resume_refuses_changed_source_or_runtime_config(self):
        self.prepare();manifest,report,home=c.verify(self.out)
        with patch.object(c,'sources',return_value={}):
            with self.assertRaisesRegex(ValueError,'source/corpus'):c.verify(self.out)
        config=c.read(home/'config/settings.json');config['threads']=3;c.write(home/'config/settings.json',config)
        with self.assertRaisesRegex(ValueError,'configuration changed'):c.verify(self.out)

    def test_resume_refuses_worker_and_manifest_changes(self):
        self.prepare()
        with patch.object(c,'check_prepared',return_value={**self.binding,'binary_sha256':'foreign'}):
            with self.assertRaisesRegex(ValueError,'worker/model'):c.verify(self.out)
        manifest=c.read(self.out/'manifest.json');manifest['scope']='CLAIM_GENUINE_USER';c.write(self.out/'manifest.json',manifest)
        with self.assertRaisesRegex(ValueError,'manifest changed'):c.verify(self.out)

    def test_coordinated_settings_and_report_optimizer_drift_is_refused(self):
        self.prepare();report=c.read(self.out/'report.json');report['configuration']['output_adapter_lr']=.15
        c.write(self.out/'isolated-home/config/settings.json',report['configuration']);c.save_report(self.out,report)
        with self.assertRaisesRegex(ValueError,'Immutable preregistered'):c.verify(self.out)

    def test_only_gated_exact_stage_modes_can_change(self):
        self.prepare();report=c.read(self.out/'report.json');report['configuration']['learning_mode']='APPROVED_COMMIT';report['configuration']['c3_decode_mode']='same_causal'
        c.write(self.out/'isolated-home/config/settings.json',report['configuration']);c.save_report(self.out,report)
        with self.assertRaisesRegex(ValueError,'Immutable preregistered'):c.verify(self.out)
        report.update(consume_started=True,fit={'stage':'PENDING_APPROVAL','report':{'metrics':{'commit_eligible':True}}});c.save_report(self.out,report)
        c.verify(self.out)

    def test_progress_cannot_skip_failed_or_unfinished_original_row(self):
        rows=c.fixture();r={'status':'COLLECTED_PARTIAL_NO_FIT','rows':[{'index':0,'fixture':rows[0],'stage':'ACCEPTED'},{'index':1,'fixture':rows[1],'stage':'EXPORTED'}]}
        with self.assertRaisesRegex(ValueError,'Unfinished'):c.validate_progress(r,rows)
        r['rows'][0]['stage']='EXPORTED';r['rows'][1]['fixture']=rows[2]
        with self.assertRaisesRegex(ValueError,'original-order'):c.validate_progress(r,rows)
        r['status']='EVALUATED_FAIL'
        with self.assertRaisesRegex(ValueError,'terminal'):c.validate_progress(r,rows)

    def test_row_limit_resume_does_not_replay_completed_native_rows(self):
        rows=c.fixture();report={'status':'COLLECTED_PARTIAL_NO_FIT','rows':[{'index':i,'fixture':rows[i],'stage':'EXPORTED'} for i in range(2)]}
        with patch.object(c,'verify',return_value=({'rows':rows},report,self.root)),patch.object(c,'Runtime',side_effect=AssertionError('No duplicate native call')):
            self.assertIs(c.collect(self.root,2),report)
            with self.assertRaisesRegex(ValueError,'truncate'):c.collect(self.root,1)

    def test_real_native_failure_is_retained_and_not_silently_retried(self):
        self.prepare();manifest,report,home=c.verify(self.out);runtime=MagicMock();runtime.store.one.return_value={'n':0};runtime.submit.return_value='TEST_ACCEPTED';runtime.cfg=DEFAULTS
        with patch.object(c,'Runtime',return_value=runtime),patch.object(c,'wait_answer',side_effect=ValueError('Actual failed reaping guard')):
            with self.assertRaisesRegex(ValueError,'reaping'):c.collect(self.out,1)
        retained=c.read(self.out/'report.json');self.assertEqual(retained['status'],'DIAGNOSTIC_FAILED');self.assertEqual(retained['rows'][0]['event_id'],'TEST_ACCEPTED');runtime.submit.assert_called_once();runtime.close.assert_called_once()
        with patch.object(c,'Runtime',side_effect=AssertionError('Retry forbidden')):
            with self.assertRaisesRegex(ValueError,'terminal'):c.collect(self.out,1)

    def test_fit_and_approval_require_complete_original_evidence(self):
        self.prepare()
        with patch.object(c,'train_dataset',side_effect=AssertionError('Incomplete fit forbidden')):
            with self.assertRaisesRegex(ValueError,'exact46'):c.fit(self.out)
        with patch.object(c,'Runtime',side_effect=AssertionError('Approval forbidden')):
            with self.assertRaisesRegex(ValueError,'test-approval'):c.consume(self.out,False)

    def test_raw_completed_copy_survives_runtime_diagnostic_pruning(self):
        source=self.root/'runtime-tmp';source.mkdir();(source/'observed.json').write_bytes(b'ACTUAL_BYTES_FIXTURE')
        row={'index':4};c.preserve(self.root,row,{'runner':{'artifact_directory':str(source)}})
        (source/'observed.json').unlink();source.rmdir();saved=self.root/row['raw_directory']/'observed.json'
        self.assertEqual(saved.read_bytes(),b'ACTUAL_BYTES_FIXTURE');self.assertEqual(row['raw_sha256']['observed.json'],file_hash(saved))

    def test_resume_rejects_tampered_permanent_raw_observation(self):
        manifest=self.prepare();report=c.read(self.out/'report.json');source=self.root/'actual-fixture';source.mkdir();(source/'observed.json').write_bytes(b'SOFTWARE_ONLY')
        row={'index':0,'fixture':manifest['rows'][0],'stage':'ANSWERED'};c.preserve(self.out,row,{'runner':{'artifact_directory':str(source)}});report['rows']=[row];c.save_report(self.out,report)
        (self.out/row['raw_directory']/'observed.json').write_bytes(b'TAMPER')
        with self.assertRaisesRegex(ValueError,'raw turn changed'):c.verify(self.out)

if __name__=='__main__':unittest.main()
