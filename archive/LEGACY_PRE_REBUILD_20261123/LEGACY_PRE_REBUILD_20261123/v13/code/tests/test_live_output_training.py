"""Software artifact/math fixtures only; no native run or genuine Human labels."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from scripts import train_live_output_adapter as live
from scripts.live_output_adapter_port import ABI,HEAD_FORMAT
from v13.common import dumps,digest,file_hash
from v13.contracts import packet
from v13.config import DEFAULTS
from v13 import output_adapter_worker as numerical
from test_output_adapter import fixture

class LiveTraining(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.abi=dict(ABI,model_sha256='a'*64,worker_sha256='b'*64,worker_sources={'software_fixture':'c'*64},library_sha256={'libllama.so':'d'*64},runner_tag='SOFTWARE_FIXTURE')
        self.cfg={key:DEFAULTS[key] for key in ('output_adapter_steps','output_adapter_lr','max_update_norm','retention_max_delta','output_adapter_max_bias','output_adapter_support_cosine')}
        self.query='Software fixture query';self.label='Software fixture human-label text'
        self.context={'messages':[{'role':'user','content':self.query}],'prompt':'Software template','token_ids':[7,8],'history_trimmed':False};context_sha=digest(dumps(self.context))
        self.entry={}
        self.write('context',self.context);self.write('tokens',{'token_ids':[7,8],'context_source_sha256':context_sha})
        self.write('query_source',self.query,text=True);self.write('label_source',self.label,text=True)
        self.write('features',{'schema':ABI['feature_schema'],'pid':42,'token_ids':[7,8],'live_last_state':[1.]+[0.]*1023,'first_position':{'logits':[0.]*65536,'probabilities':[1./65536]*65536},'context_source_sha256':context_sha,'model_sha256':'a'*64,'lib_sha256':'d'*64})
        handle={'handle_id':'handle-software-fixture','pid':42,'features_sha256':self.entry['features']['sha256'],'token_file_sha256':self.entry['tokens']['sha256'],'context_source_sha256':context_sha,'model_sha256':'a'*64,'lib_sha256':'d'*64}
        self.write('result',{'status':'PAUSE_RESUME_DIAGNOSTIC_COMPLETE','pid':42,'handle':handle,'token_ids':[7,8],'context_source_sha256':context_sha,'token_file_sha256':self.entry['tokens']['sha256'],'same_context_lifetime':True,'resume_prefill_calls':0,'handle_consumed':True})
        self.write('observed',{'feature_abi':self.abi,'feature':[1.]+[0.]*1023,'native_prompt_token_ids':[7,8],'prompt_sha256':digest('Software template'),'native_context_binding':dict(handle,scope='EXACT_SAME_CAUSAL_PREFILL',live_generation_kv_tap=True)})
        ref={'source_id':'SOFTWARE_LABEL_SOURCE','sha256':self.entry['label_source']['sha256'],'char_start':0,'char_end':len(self.label),'modality':'text'}
        self.decision=packet('HumanDecision','F5_HUMAN_CONTROL','SOFTWARE_EVENT','SOFTWARE_GENERATION',kind='output',value=self.label,learning_permission='learn',source_ref=ref,
                             selection={'context_ref':{'sha256':digest(dumps(self.context['messages']))},'target_position':0,'feature_abi':self.abi,'live_observation_sha256':self.entry['observed']['sha256']})
        self.write('human_decision',self.decision);self.write('label_tokenization',{'source_sha256':self.entry['label_source']['sha256'],'model_sha256':'a'*64,'worker_sha256':'b'*64,'add_special':False,'token_ids':[1,9]})
        self.dataset=self.root/'dataset.json';self.save_dataset()
    def tearDown(self):self.tmp.cleanup()
    def write(self,name,value,text=False):
        path=self.root/(name+'.json');path.write_text(value if text else dumps(value));self.entry[name]={'path':path.name,'sha256':file_hash(path)}
    def save_dataset(self,**extra):
        self.dataset.write_text(dumps(dict(schema=live.SCHEMA,config=self.cfg,feature_abi=self.abi,token_ids=[1,2],observations=[self.entry],**extra)))
    def test_full_artifact_bindings_extract_selected_and_unchanged_probability_mass(self):
        inp,abi,_=live.prepare(self.dataset);self.assertEqual(abi,self.abi);self.assertEqual(inp['target_indices'],[0]);self.assertEqual(inp['source_groups'],[digest(self.query)])
        self.assertAlmostEqual(sum(np.exp(inp['base_log_probabilities'][0])),1.)
        report=live.validate_only(self.dataset,self.root/'validate');self.assertEqual(report['status'],'INSUFFICIENT_LABELLED_COHORT');self.assertEqual(report['optimizer_steps'],0)
    def test_revoked_permission_and_changed_label_tokenization_refuse_training(self):
        decision=copy.deepcopy(self.decision);decision['learning_permission']='record';self.write('human_decision',decision);self.save_dataset()
        with self.assertRaisesRegex(ValueError,'--learn'):live.prepare(self.dataset)
        self.write('human_decision',self.decision);self.write('label_tokenization',{'source_sha256':'wrong','token_ids':[1]});self.save_dataset()
        with self.assertRaisesRegex(ValueError,'label tokenization'):live.prepare(self.dataset)
    def test_same_dimensional_old_or_other_feature_abi_is_rejected(self):
        observed=json.loads((self.root/'observed.json').read_text());observed['feature_abi']['n_batch']=512;self.write('observed',observed)
        decision=copy.deepcopy(self.decision);decision['selection']['live_observation_sha256']=self.entry['observed']['sha256'];self.write('human_decision',decision);self.save_dataset()
        with self.assertRaisesRegex(ValueError,'same-ABI'):live.prepare(self.dataset)
    def test_duplicate_source_group_and_tampered_raw_feature_fail(self):
        d=json.loads(self.dataset.read_text());d['observations'].append(d['observations'][0]);self.dataset.write_text(dumps(d))
        with self.assertRaisesRegex(ValueError,'Repeated source'):live.prepare(self.dataset)
        self.save_dataset();(self.root/'features.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'bytes changed'):live.prepare(self.dataset)
    def test_legacy_active_checkpoint_cannot_convert_weights_or_normalizer(self):
        path=self.root/'legacy.npz';np.savez(path,format='c3-native-first-token-delta-v2',weights=np.ones((1025,2)))
        self.save_dataset(active_checkpoint={'path':path.name,'sha256':file_hash(path)})
        before=file_hash(path)
        with self.assertRaisesRegex(ValueError,'cannot be converted'):live.prepare(self.dataset)
        self.assertEqual(file_hash(path),before)
    def test_unchanged_optimizer_gates_new_format_reload_and_contradictory_retention(self):
        # Only this numerical test bypasses artifact loading. These are explicitly
        # synthetic unit vectors/probabilities, not native or human proof artifacts.
        data=fixture();data['active_checkpoint']=None;old_format=numerical.FORMAT
        with patch.object(live,'prepare',return_value=(data,self.abi,[])):
            first=live.train_dataset(self.dataset,self.root/'fit')
        self.assertTrue(first['metrics']['gradient_check']);self.assertTrue(first['metrics']['commit_eligible']);self.assertTrue(first['metrics']['live_checkpoint_reload'])
        candidate=self.root/'fit/candidate.npz'
        with np.load(candidate,allow_pickle=False) as a:
            self.assertEqual(str(a['format']),HEAD_FORMAT);self.assertEqual(json.loads(str(a['feature_abi'])),self.abi)
            self.assertTrue(len(a['retention_ids'])>0)
        contradiction=fixture();contradiction['active_checkpoint']=str(candidate);contradiction['target_indices']=[1-y for y in contradiction['target_indices']]
        with patch.object(live,'prepare',return_value=(contradiction,self.abi,[])):
            second=live.train_dataset(self.dataset,self.root/'retention-failure')
        self.assertFalse(second['metrics']['retention_pass']);self.assertFalse(second['metrics']['commit_eligible']);self.assertEqual(numerical.FORMAT,old_format)
        self.assertEqual(first['approval_authority'],0);self.assertFalse(first['production_integration'])

if __name__=='__main__':unittest.main()
