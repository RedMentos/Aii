"""SOFTWARE: synthetic native math, real isolated SQLite F5/generation lifecycle.
Native parser is patched ONLY for the explicitly synthetic numeric fit fixture.
"""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from v13.common import dumps,digest,file_hash
from v13.runtime import Runtime
from v13.operator import Operator
from v13 import causal_output
from scripts import train_live_output_adapter as live
from scripts.export_live_output_dataset import persist_export_decision,select_label
from test_output_adapter import fixture

class NumericWorker:
    def __init__(self,cmd,**kw):
        self.pid=None;self.returncode=0
        live.train_dataset(cmd[cmd.index('--dataset')+1],cmd[cmd.index('--out')+1])
    def poll(self):return self.returncode

class CausalLifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Build permission lineage and fit numerical fixture ONCE; individual
        # tests clone this isolated Store and independently verify every import.
        cls.base_tmp=tempfile.TemporaryDirectory();base=Path(cls.base_tmp.name)
        cls.abi={'dimension':1024,'vocabulary':65536,'n_batch':128,'n_ubatch':128,'context_tokens':2048,'threads':2,'embeddings':False,'pooling':'NONE','feature_schema':'V13_PAUSED_CAUSAL_STREAM_FEATURES_V2','stream_abi':'SOFTWARE_FIXTURE_NOT_NATIVE','model_sha256':'a'*64,'worker_sha256':'b'*64,'worker_sources':{'SOFTWARE_FIXTURE':'c'*64},'library_sha256':{'SOFTWARE_FIXTURE':'d'*64},'runner_tag':'SOFTWARE_FIXTURE'}
        cls.data=fixture();cls.data['active_checkpoint']=None;cls.entries=[];cls.originals=[];groups=[]
        r=Runtime(base/'home');r.cfg.update(learning_mode='SHADOW_UPDATE',**cls.data['config'])
        cohort=base/'cohort';cohort.mkdir()
        try:
            for i in range(len(cls.data['source_groups'])):
                query='SOFTWARE test query '+str(i);label='Authored SOFTWARE reference '+str(i%2)
                e=r.store.event(r.session,query);r._causal_output_context(e,[{'role':'user','content':query}],[]);r.learner.output_feedback(e['event_id'],label,'learn')
                raw=r.store.one("SELECT payload FROM packets WHERE kind='HumanDecision' AND event_id=?",(e['event_id'],))['payload'];d=json.loads(raw)
                selected=select_label(r.store,d['packet_id'],d['source_ref']['source_id'],'unavailable',True)
                folder=cohort/str(i);folder.mkdir();(folder/'observed.json').write_text(dumps({'feature':cls.data['native_features'][i],'feature_abi':cls.abi,'software_fixture':True}))
                derived=persist_export_decision(r.store,selected,folder/'observed.json',cls.abi,True)
                (folder/'human_decision.json').write_text(dumps(derived));(folder/'query_source.json').write_text(query);(folder/'label_source.json').write_text(label)
                cls.entries.append({k:{'path':str((folder/(k+'.json')).relative_to(cohort)),'sha256':file_hash(folder/(k+'.json'))} for k in ['observed','human_decision','query_source','label_source']})
                cls.originals.append(selected);groups.append(digest(query))
        finally:r.close()
        cls.data['source_groups']=groups
        dataset=cohort/'dataset.json';dataset.write_text(dumps({'schema':live.SCHEMA,'config':cls.data['config'],'feature_abi':cls.abi,'token_ids':[123,456],'observations':cls.entries}))
        with patch.object(live,'prepare',return_value=(cls.data,cls.abi,[])):live.train_dataset(dataset,base/'fitted')
    @classmethod
    def tearDownClass(cls):cls.base_tmp.cleanup()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        for folder in ['home','cohort','fitted']:shutil.copytree(Path(self.base_tmp.name)/folder,self.root/folder)
        self.home=self.root/'home';self.dataset=self.root/'cohort/dataset.json';self.trained=self.root/'fitted';self.r=Runtime(self.home);self.r.cfg.update(learning_mode='SHADOW_UPDATE',**self.data['config'])
        self.preparer=patch.object(live,'prepare',return_value=(self.data,self.abi,[]));self.preparer.start()
        self.binding=patch('v13.causal_prepare.check_prepared',return_value={'feature_abi':self.abi});self.binding.start()
    def tearDown(self):self.binding.stop();self.preparer.stop();self.r.close();self.tmp.cleanup()
    def import_candidate(self):
        with patch('v13.learning.subprocess.Popen',side_effect=NumericWorker):result=self.r.learner.import_causal_output(self.dataset,self.trained)
        self.update=result.split()[0];return self.r.store.one('SELECT * FROM updates WHERE id=?',(self.update,))
    def approve(self):self.r.cfg['learning_mode']='APPROVED_COMMIT';return Operator(self.r).run(':approve '+self.update)
    def observed(self):return {'feature':self.data['native_features'][0],'feature_abi':self.abi}
    def test_fit_import_pending_approval_restart_consume_rollback(self):
        before=self.r.store.generation_id;row=self.import_candidate();self.assertEqual(row['status'],'PENDING_APPROVAL');self.assertEqual(before,self.r.store.generation_id)
        self.assertEqual(causal_output.approved_prediction(self.r.learner,self.observed()),(None,'NO_APPROVED_SAME_CAUSAL_COMPONENT'))
        self.assertNotEqual(self.approve(),before);result,reason=causal_output.approved_prediction(self.r.learner,self.observed())
        self.assertEqual(reason,'APPROVED_SAME_CAUSAL_FIRST_TOKEN_DELTA');self.assertTrue(result['individually_approved']);self.assertTrue(result['first_token_bias'])
        self.r.close();self.r=Runtime(self.home);self.assertEqual(causal_output.approved_prediction(self.r.learner,self.observed())[0]['approved_update_id'],self.update)
        Operator(self.r).run(':rollback '+self.update);self.assertEqual(causal_output.approved_prediction(self.r.learner,self.observed()),(None,'NO_APPROVED_SAME_CAUSAL_COMPONENT'))
    def test_direct_store_commit_mode_and_revoked_permission_guards(self):
        self.import_candidate()
        with self.assertRaisesRegex(ValueError,'APPROVED_COMMIT'):self.r.store.switch_generation(self.update,self.r.cfg,self.r.revisions())
        self.r.cfg['learning_mode']='APPROVED_COMMIT';self.r.learner.output_feedback(self.originals[0]['event']['event_id'],'record-only revocation','record')
        with self.assertRaisesRegex(ValueError,'superseded|authorization|revoked'):self.r.store.switch_generation(self.update,self.r.cfg,self.r.revisions())
    def test_active_permission_revocation_refuses_consume(self):
        self.import_candidate();self.approve();self.r.learner.output_feedback(self.originals[0]['event']['event_id'],'record-only revocation','record')
        with self.assertRaises(ValueError):causal_output.approved_prediction(self.r.learner,self.observed())
    def test_support_and_foreign_same_dimensional_abi_refuse_delta(self):
        self.import_candidate();self.approve();alien=np.zeros(1024);alien[-1]=1
        result,reason=causal_output.approved_prediction(self.r.learner,{'feature':alien.tolist(),'feature_abi':self.abi});self.assertFalse(result['in_support']);self.assertEqual(result['first_token_bias'],[]);self.assertEqual(reason,'OUT_OF_SUPPORT')
        abi=copy.deepcopy(self.abi);abi['n_batch']=512
        with self.assertRaises(ValueError):causal_output.approved_prediction(self.r.learner,{'feature':self.data['native_features'][0],'feature_abi':abi})
    def test_tampered_candidate_or_fit_receipt_refuses_approval(self):
        row=self.import_candidate();m=json.loads(row['manifest']);(self.home/m['verified_shadow_report']['path']).write_text('{}')
        with self.assertRaisesRegex(ValueError,'receipt'):self.approve()
    def test_failed_numeric_gate_cannot_be_declared_eligible(self):
        row=self.import_candidate();m=json.loads(row['manifest']);m['metrics']['utility_pass']=False
        with self.r.store.tx() as c:c.execute('UPDATE updates SET manifest=? WHERE id=?',(dumps(m),self.update))
        with self.assertRaisesRegex(ValueError,'gates'):self.approve()
    def test_exported_permission_must_exist_in_actual_store(self):
        path=self.root/'cohort'/self.entries[0]['human_decision']['path'];d=json.loads(path.read_text());d['packet_id']='not-stored';path.write_text(dumps(d))
        dataset=json.loads(self.dataset.read_text());dataset['observations'][0]['human_decision']['sha256']=file_hash(path);self.dataset.write_text(dumps(dataset))
        self.trained=self.root/'changed-fit';live.train_dataset(self.dataset,self.trained)
        with self.assertRaisesRegex(ValueError,'actual current Store'):self.import_candidate()
    def test_foreign_or_legacy_head_is_never_converted(self):
        row=self.import_candidate();m=json.loads(row['manifest']);m['feature_abi']=copy.deepcopy(m['feature_abi']);m['feature_abi']['n_batch']=512
        with self.r.store.tx() as c:c.execute('UPDATE updates SET manifest=? WHERE id=?',(dumps(m),self.update))
        with self.assertRaisesRegex(ValueError,'exact current'):self.approve()
    def test_decode_operator_reversible_persisted_and_busy_guarded(self):
        op=Operator(self.r);op.run(':decode same_causal');self.assertEqual(self.r.cfg['answer_tokens'],64);op.run(':decode same_causal_zero');self.assertEqual(self.r.cfg['c3_decode_mode'],'same_causal_zero')
        op.run(':decode server');self.r.close();self.r=Runtime(self.home);self.assertEqual(self.r.cfg['c3_decode_mode'],'server')
        with patch.object(self.r,'idle',return_value=False),self.assertRaises(ValueError):Operator(self.r).run(':decode same_causal')

if __name__=='__main__':unittest.main()
