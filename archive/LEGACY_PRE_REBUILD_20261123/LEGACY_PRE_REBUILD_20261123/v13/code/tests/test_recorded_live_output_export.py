"""Explicit SYNTHETIC software fixtures; never a native execution proof."""
import copy
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np
from scripts import export_recorded_live_output_dataset as recorded
from scripts.native_prefill_stream_client import ABI,STREAM_ABI
from scripts.train_live_output_adapter import prepare,SCHEMA
from v13.common import dumps,digest,file_hash
import test_live_output_export as existing

class RecordedExport(unittest.TestCase):
    def setUp(self):
        self.base=existing.LiveExport();self.base.setUp();self.addCleanup(self.base.tearDown)
        self.home=self.base.home;self.root=self.base.root;self.store=self.base.s;self.selected=self.base.selected()
        self.folder=self.home/'tmp'/('c3-causal-stream-'+'1'*32);self.folder.mkdir()
        self.libraries={}
        for i,name in enumerate(('libllama.so','libggml.so','libggml-base.so','libggml-cpu.so')):
            path=self.root/name;path.write_bytes(('SYNTHETIC_LIBRARY_'+str(i)).encode());self.libraries[str(path)]=file_hash(path)
        self.ident={'model_sha256':'a'*64,'server_sha256':'e'*64,'libraries':self.libraries,'llama_library':str(self.root/'libllama.so')}
        self.abi=dict(ABI,model_sha256='a'*64,worker_sha256='b'*64,worker_sources={'scripts/native_prefill_stream.cpp':'c'*64},library_sha256={Path(p).name:v for p,v in self.libraries.items()},runner_tag='SYNTHETIC_SOFTWARE_TEST')
        self.binding={'feature_abi':self.abi,'binary_sha256':'b'*64,'identity':self.ident,'source_hashes':{'scripts/native_prefill_stream.cpp':'c'*64}}
        self.context={'messages':self.selected['messages'],'prompt':'SYNTHETIC_TEMPLATE','token_ids':[7,8],'history_trimmed':False};sha=digest(dumps(self.context))
        self.write('context',self.context);self.write('tokens',{'token_ids':[7,8],'context_source_sha256':sha});self.write('pins',{'libraries':self.libraries})
        logits=[0.]*65536;logits[1]=1.;p=np.exp(np.asarray(logits)-1.);p/=p.sum()
        self.features={'schema':ABI['feature_schema'],'feature_abi':STREAM_ABI,'worker_source_sha256':'c'*64,'pid':424242,'token_ids':[7,8],'live_last_state':[1.]+[0.]*1023,'first_position':{'logits':logits,'probabilities':p.tolist(),'greedy_token_id':1},'context_source_sha256':sha,'model_sha256':'a'*64,'lib_sha256':self.libraries[self.ident['llama_library']]}
        self.write('features',self.features)
        self.handle={'schema':'V13_CAUSAL_STREAM_HANDLE_V2','feature_abi':STREAM_ABI,'worker_source_sha256':'c'*64,'executable_sha256':'b'*64,'max_tokens':64,'nonce':'2'*32,'pid':424242,'model_sha256':'a'*64,'lib_sha256':self.features['lib_sha256'],'backend_pins_sha256':file_hash(self.folder/'pins.json'),'token_file_sha256':file_hash(self.folder/'tokens.json'),'context_source_sha256':sha,'features_sha256':file_hash(self.folder/'features.json'),'sequence_id':0,'next_position':2,'context_tokens':2048,'prefill_generation':1,'wait_ttl_seconds':15}
        self.handle['handle_id']=digest(dumps(self.handle))
        self.command={'command':'resume','handle_id':self.handle['handle_id'],'nonce':'2'*32,'context_source_sha256':sha,'feature_abi':STREAM_ABI,'worker_source_sha256':'c'*64,'bias':[]};self.write('resume',self.command)
        self.events=[{'event':'TOKEN','sequence':0,'token_id':1,'piece_hex':'','text':'','text_encoding':'UTF8_WITH_REPLACEMENT_IF_PARTIAL; piece_hex_is_exact','is_eog':True,'first_position_bias':False,'handle_id':self.handle['handle_id'],'feature_abi':STREAM_ABI}];self.write('events',self.events)
        loaded=[{'path':p,'sha256':v} for p,v in self.libraries.items()]
        self.result={'status':'CAUSAL_STREAM_DIAGNOSTIC_COMPLETE','pid':424242,'handle':self.handle,'accepted_command':self.command,'same_context_lifetime':True,'resume_prefill_calls':0,'handle_consumed':True,'additional_commands_accepted':0,'token_ids':[7,8],'token_file_sha256':self.handle['token_file_sha256'],'context_source_sha256':sha,'all_loaded_libraries_verified':True,'backend_pins_sha256':self.handle['backend_pins_sha256'],'model':{'sha256':'a'*64},'model_sha256_after':'a'*64,'feature_abi':STREAM_ABI,'worker_source_sha256':'c'*64,'executable_sha256':'b'*64,'bias_applied_positions':0,'first_native_greedy_token_id':1,'first_biased_token_id':1,'loaded_llama_library':loaded[0],'loaded_ggml_library':loaded[1],'loaded_ggml_base_library':loaded[2],'loaded_cpu_backend_libraries':loaded[3:],'decoded_native_token_ids':[1],'continuation':[],'max_tokens':64,'generated_token_count':1,'decoded_native_preview_hex':'','decoded_native_preview_sha256':digest(b''),'resume_decode_calls':0,'unbiased_continuation_steps':0,'stop_reason':'EOS'};self.write('result',self.result)
        self.observed={'feature':self.features['live_last_state'],'feature_abi':self.abi,'native_prompt_token_ids':[7,8],'prompt_sha256':digest(self.context['prompt']),'base_log_probabilities':None,'native_context_binding':{'scope':'EXACT_SAME_CAUSAL_PREFILL','live_generation_kv_tap':True,'handle_id':self.handle['handle_id'],'context_source_sha256':sha,'features_sha256':self.handle['features_sha256'],'pid':424242}};self.write('observed',self.observed)
        self.controller={'status':'SAME_CONTEXT_STREAM_COMPLETE','process_reaped':True,'exit_code':0,'resume_commands_sent':1,'pid':424242,'checks':{'SYNTHETIC_CHECK':True}};self.write('controller',self.controller)
        self.runner={'status':'FINAL','role':'C3_LANGUAGE','decode_mode':'same_causal_zero','process_reaped':True,'artifact_directory':str(self.folder),'causal_controller':self.controller,'feature_abi':self.abi,'native_token_ids':[1],'template_release':{'process_reaped':True},'observed_sha256':file_hash(self.folder/'observed.json')}
        self.mid=self.store.message(self.base.r.session,self.base.event['event_id'],'assistant')
        self.store.finish_message(self.mid,'FINAL',{'model_generated':True,'runner':self.runner})
        self.tok={'source_sha256':digest(self.selected['label']),'model_sha256':'a'*64,'worker_sha256':'b'*64,'token_ids':[1,9],'add_special':False,'tokenizer':'PINNED_LLAMA_RUNNER_HTTP_TOKENIZE','server_sha256':'e'*64}
        self.receipt={'schema':recorded.RECEIPT,'status':'ACTUAL_LABEL_TOKENIZED_REAPED','feature_abi':self.abi,'model_revision':'SOFTWARE_REVISION','request':{'content':self.selected['label'],'add_special':False},'response':{'tokens':[1,9]},'release':{'process_reaped':True},'label_tokenization':self.tok}
        self.receipt_path=self.root/'receipt.json';self.receipt_path.write_text(dumps(self.receipt))
    def write(self,name,value):(self.folder/(name+'.json')).write_text(dumps(value))
    def validate(self):return recorded.validate_record(self.folder,self.runner,self.selected,self.binding)
    def test_completed_record_independently_checks_actual_events_and_hashes(self):
        _,hashes,checks=self.validate();self.assertTrue(all(checks.values()));self.assertEqual(hashes['observed'],file_hash(self.folder/'observed.json'))
        bad=copy.deepcopy(self.events);bad[0]['token_id']=2;self.write('events',bad)
        with self.assertRaisesRegex(ValueError,'completion binding'):self.validate()
    def test_complete_controller_cannot_replace_raw_completion(self):
        bad=copy.deepcopy(self.result);bad['resume_prefill_calls']=1;self.write('result',bad)
        with self.assertRaisesRegex(ValueError,'completion binding'):self.validate()
        self.write('result',self.result);bad=copy.deepcopy(self.controller);bad['process_reaped']=False;self.write('controller',bad)
        with self.assertRaisesRegex(ValueError,'reaped Runtime controller'):self.validate()
    def test_observation_context_library_and_abi_tampering_rejected(self):
        bad=copy.deepcopy(self.observed);bad['feature'][0]=2.;self.write('observed',bad)
        with self.assertRaisesRegex(ValueError,'observation bytes changed'):self.validate()
        self.write('observed',self.observed);bad=copy.deepcopy(self.context);bad['messages']=[{'role':'user','content':'OTHER_SOURCE'}];self.write('context',bad)
        with self.assertRaisesRegex(ValueError,'context/source'):self.validate()
        self.write('context',self.context);binding=copy.deepcopy(self.binding);binding['feature_abi']['model_sha256']='f'*64
        with self.assertRaisesRegex(ValueError,'exact-ABI'):recorded.validate_record(self.folder,self.runner,self.selected,binding)
        (self.root/'libllama.so').write_bytes(b'OTHER_LIBRARY')
        with self.assertRaisesRegex(ValueError,'libraries'):self.validate()
    def test_missing_original_runtime_observation_hash_cannot_reconstruct_record(self):
        runner=dict(self.runner);runner.pop('observed_sha256')
        with self.assertRaisesRegex(ValueError,'bytes changed or unbound'):recorded.validate_record(self.folder,runner,self.selected,self.binding)
    def test_recorded_answer_rejects_noncompleted_and_external_artifacts(self):
        folder,_,mid=recorded.recorded_answer(self.store,self.selected,self.home);self.assertEqual(mid,self.mid);self.assertEqual(folder,self.folder)
        with self.store.tx() as c:c.execute('UPDATE messages SET status=? WHERE id=?',('DEADLINE',self.mid))
        with self.assertRaisesRegex(ValueError,'Completed reaped'):recorded.recorded_answer(self.store,self.selected,self.home)
        bad=dict(self.runner,artifact_directory=str(self.root/'outside'))
        with self.store.tx() as c:c.execute('UPDATE messages SET status=?,metadata=? WHERE id=?',('FINAL',dumps({'model_generated':True,'runner':bad}),self.mid))
        with self.assertRaisesRegex(ValueError,'nonce/path'):recorded.recorded_answer(self.store,self.selected,self.home)
    def test_exact_receipt_rejects_changed_text_server_parameters_and_reaping(self):
        self.assertEqual(recorded.validate_receipt(self.receipt_path,self.selected['label'],self.binding,'SOFTWARE_REVISION'),self.tok)
        for change in ('request','server','release','revision'):
            bad=copy.deepcopy(self.receipt)
            if change=='request':bad['request']['add_special']=True
            elif change=='server':bad['label_tokenization']['server_sha256']='f'*64
            elif change=='release':bad['release']['process_reaped']=False
            else:bad['model_revision']='OTHER'
            self.receipt_path.write_text(dumps(bad))
            with self.assertRaisesRegex(ValueError,'tokenizer receipt'):recorded.validate_receipt(self.receipt_path,self.selected['label'],self.binding,'SOFTWARE_REVISION')
    def test_offline_export_reuses_bytes_and_existing_trainer_schema(self):
        self.store.close();out=self.root/'portable'
        with patch.object(recorded,'bind_installed',return_value=self.binding),patch.object(recorded,'verify_binding'),patch.object(recorded,'ModelManager',return_value=SimpleNamespace(revision=lambda _:'SOFTWARE_REVISION')),patch.object(recorded,'LlamaRunner',side_effect=AssertionError('export must not call native runner')):
            report=recorded.export_recorded(self.home,out,self.base.id,self.base.source,self.receipt_path,True)
        self.assertEqual(report['status'],'RECORDED_CAUSAL_LABEL_EXPORTED');self.assertFalse(report['native_calls']);self.assertEqual(report['prefill_calls'],0)
        fragment=json.loads((out/'fragment.json').read_text());self.assertEqual(file_hash(out/'observed.json'),file_hash(self.folder/'observed.json'))
        dataset=out/'test-only-dataset.json';dataset.write_text(dumps({'schema':SCHEMA,'feature_abi':self.abi,'config':{k:recorded.DEFAULTS[k] for k in recorded.original.KNOB_NAMES},'token_ids':[1,2],'observations':[fragment['observation']]}))
        inp,_,_=prepare(dataset);self.assertEqual(inp['target_indices'],[0]);self.assertEqual(fragment['recorded_runtime_evidence']['prefill_calls'],0)
    def test_current_permission_and_active_coordinator_reject_before_export(self):
        with patch.object(recorded,'bind_installed',side_effect=AssertionError('must not bind while active')):
            with self.assertRaisesRegex(RuntimeError,'läuft bereits'):recorded.export_recorded(self.home,self.root/'blocked',self.base.id,self.base.source,self.receipt_path,True)
            with self.assertRaisesRegex(RuntimeError,'läuft bereits'):recorded.tokenize_label(self.home,self.root/'blocked-tokenizer',self.base.id,self.base.source,True)
        with self.store.tx() as c:c.execute('UPDATE feedback SET permission=? WHERE source_id=?',('record',self.base.source))
        self.store.close()
        with patch.object(recorded,'bind_installed',return_value=self.binding),patch.object(recorded,'ModelManager',return_value=SimpleNamespace(revision=lambda _:'SOFTWARE_REVISION')):
            with self.assertRaisesRegex(ValueError,'revoked'):recorded.export_recorded(self.home,self.root/'revoked',self.base.id,self.base.source,self.receipt_path,True)
        self.assertFalse((self.root/'revoked').exists())
    def test_both_cli_commands_refuse_active_coordinator_before_native(self):
        for command in ('export','tokenize'):
            out=self.root/('cli-blocked-'+command)
            args=[sys.executable,str(recorded.APP/'scripts/export_recorded_live_output_dataset.py'),command,'--installed-home',str(self.home),'--out',str(out),'--decision',self.base.id,'--label-source',self.base.source,'--learn']
            if command=='export':args+=['--tokenizer-receipt',str(self.receipt_path)]
            completed=subprocess.run(args,capture_output=True,text=True,timeout=10)
            self.assertEqual(completed.returncode,2,completed.stderr);response=json.loads(completed.stdout)
            self.assertIn('läuft bereits',response['error']);self.assertFalse(out.exists())
    def test_budgets_and_existing_output_are_not_mutated(self):
        for seconds in (True,0,91,5.5):
            with self.assertRaises(ValueError):recorded.bounded(seconds)
        self.store.close();out=self.root/'existing';out.mkdir();(out/'keep').write_text('UNCHANGED')
        with patch.object(recorded,'bind_installed',return_value=self.binding),patch.object(recorded,'ModelManager',return_value=SimpleNamespace(revision=lambda _:'SOFTWARE_REVISION')):
            with self.assertRaisesRegex(ValueError,'separate portable'):recorded.export_recorded(self.home,out,self.base.id,self.base.source,self.receipt_path,True)
        self.assertEqual(sorted(p.name for p in out.iterdir()),['keep'])

if __name__=='__main__':unittest.main()
