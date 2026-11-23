"""Real subprocess protocol tests with explicit NONNATIVE software fixtures."""
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import numpy as np
from scripts import live_output_adapter_port as port
from v13.common import Cancelled,Limits,Unavailable,dumps,file_hash

WORKER=r'''#!/usr/bin/env python3
# NONNATIVE SOFTWARE PROTOCOL FIXTURE. No model or inference is performed.
import hashlib,json,os,sys,time
from pathlib import Path
args=dict(zip(sys.argv[1::2],sys.argv[2::2]));MODE=__MODE__
if MODE=='hang':time.sleep(20);sys.exit(1)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,obj):Path(p).write_text(json.dumps(obj,sort_keys=True,separators=(',',':')))
tokens=json.loads(Path(args['--tokens']).read_text())['token_ids'];pid=os.getpid()
f={'schema':'V13_PAUSED_CAUSAL_PREFILL_FEATURES_V1','pid':pid,'token_ids':tokens,'live_last_state':[1.]+[0.]*1023,
   'first_position':{'logits':[0.]*65536,'probabilities':[1./65536]*65536,'greedy_token_id':0},
   'context_source_sha256':args['--context-source-sha256'],'model_sha256':args['--model-sha256'],'lib_sha256':args['--lib-sha256']}
if MODE=='bad_token':f['token_ids']=tokens+[9]
if MODE=='bad_library':f['lib_sha256']='0'*64
if MODE=='bad_distribution':f['first_position']['probabilities']=[0.]*65536
save(args['--features'],f)
h={'schema':'V13_CAUSAL_PREFILL_HANDLE_V1','nonce':args['--nonce'],'pid':pid,'model_sha256':args['--model-sha256'],
   'lib_sha256':args['--lib-sha256'],'backend_pins_sha256':sha(args['--backend-pins']),'token_file_sha256':sha(args['--tokens']),
   'context_source_sha256':args['--context-source-sha256'],'features_sha256':sha(args['--features']),
   'sequence_id':0,'next_position':len(tokens),'context_tokens':2048,'prefill_generation':1,'wait_ttl_seconds':15}
if MODE=='bad_nonce':h['nonce']='wrong'
h['handle_id']=hashlib.sha256(json.dumps(h,sort_keys=True,separators=(',',':')).encode()).hexdigest()
ready={'status':'PREFILLED_READY','handle':h,'features_path':args['--features']}
print(json.dumps(ready),flush=True)
if MODE=='duplicate_ready':print(json.dumps(ready),flush=True)
command=json.loads(sys.stdin.readline())
biased=[0.]*65536
for token,value in command['bias']:biased[token]+=value
first=max(range(65536),key=lambda i:biased[i])
libs=json.loads(Path(args['--backend-pins']).read_text())['libraries'];rows=[{'path':p,'sha256':s} for p,s in libs.items()]
raw={'software_fixture':True,'native_inference_performed':False,'status':'PAUSE_RESUME_DIAGNOSTIC_COMPLETE','pid':pid,
     'handle':h,'accepted_command':command,'handle_consumed':True,'same_context_lifetime':True,'resume_prefill_calls':0,
     'additional_commands_accepted':0,'token_ids':tokens,'token_file_sha256':sha(args['--tokens']),
     'context_source_sha256':args['--context-source-sha256'],'all_loaded_libraries_verified':True,
     'backend_pins_sha256':sha(args['--backend-pins']),'resume_decode_calls':3,'unbiased_continuation_steps':3,
     'continuation':[{'bias_applied':False,'input_token_id':first,'greedy_next_token_id':first,'position':len(tokens)+i} for i in range(3)],'bias_applied_positions':1 if command['bias'] else 0,
     'first_native_greedy_token_id':0,'first_biased_token_id':first,
     'model':{'sha256':args['--model-sha256']},'loaded_llama_library':rows[0],'loaded_ggml_library':rows[1],
     'loaded_ggml_base_library':rows[2],'loaded_cpu_backend_libraries':rows[3:],
     'decoded_native_preview':'SOFTWARE FIXTURE','decoded_native_token_ids':[first]*4}
if MODE=='extra_prefill':raw['resume_prefill_calls']=1
if MODE=='wrong_first_delta':raw['first_biased_token_id']=65535
save(args['--output'],raw)
print(json.dumps({'status':'PAUSE_RESUME_DIAGNOSTIC_COMPLETE','handle_consumed':True}),flush=True)
'''

class LiveOutputPort(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.cancel=threading.Event()
        self.context={'messages':[{'role':'user','content':'software fixture'}],'prompt':'exact software fixture template','token_ids':[1,2,3],'history_trimmed':False}
    def tearDown(self):self.tmp.cleanup()
    def binding(self,mode='normal'):
        binary=self.root/('worker-'+mode+'.py');binary.write_text(WORKER.replace('__MODE__',repr(mode)));binary.chmod(0o700)
        model=self.root/'software.model';model.write_bytes(b'explicit software fixture')
        libraries={}
        for stem in ('libllama','libggml','libggml-base','libggml-cpu'):
            p=self.root/(stem+'.so');p.write_text(stem);libraries[str(p)]=file_hash(p)
        identity={'model_path':str(model),'model_sha256':file_hash(model),'server_path':str(binary),'server_sha256':file_hash(binary),
                  'libraries':libraries,'llama_library':str(self.root/'libllama.so')}
        b={'binary':str(binary),'binary_sha256':file_hash(binary),'identity':identity,'source_hashes':{},'runner_tag':'SOFTWARE_FIXTURE_NOT_NATIVE'}
        b['feature_abi']=port.feature_abi(b);return b
    def session(self,mode='normal',**kwargs):
        return port.PausedOutputSession(self.binding(mode),self.context,self.root/('out-'+mode),self.cancel,time.monotonic()+5,**kwargs)
    def test_one_observation_one_resume_same_child_no_extra_prefill(self):
        with self.session() as s:
            observation=s.pause([0,1]);pid=s.proc.pid;result=s.resume([[7,2.]])
            self.assertEqual(result['metrics']['resume_commands_sent'],1);self.assertTrue(result['metrics']['process_reaped'])
            self.assertEqual(observation['native_context_binding']['pid'],pid)
            self.assertEqual(result['raw_result']['pid'],pid)
            self.assertEqual(len(observation['feature']),1024);self.assertEqual(len(observation['base_log_probabilities']),3)
            self.assertEqual(result['raw_result']['resume_prefill_calls'],0)
            self.assertEqual(result['native_token_ids'][0],7)
            self.assertTrue(result['raw_result']['software_fixture']);self.assertFalse(result['raw_result']['native_inference_performed'])
            with self.assertRaises(Unavailable):s.resume([])
    def test_token_nonce_library_and_distribution_mismatch_reap_before_resume(self):
        for mode in ('bad_token','bad_nonce','bad_library','bad_distribution'):
            with self.subTest(mode=mode):
                s=self.session(mode)
                with self.assertRaises(Unavailable),s:s.pause()
                self.assertTrue(s.metrics['process_reaped']);self.assertEqual(s.metrics['resume_commands_sent'],0)
    def test_duplicate_ready_and_extra_prefill_rejected_after_one_resume(self):
        for mode in ('duplicate_ready','extra_prefill','wrong_first_delta'):
            with self.subTest(mode=mode):
                s=self.session(mode)
                with self.assertRaises(Unavailable),s:s.pause();s.resume([])
                self.assertTrue(s.metrics['process_reaped']);self.assertEqual(s.metrics['resume_commands_sent'],1)
    def test_cancel_and_absolute_deadline_kill_and_reap_actual_waiting_child(self):
        s=self.session('hang');timer=threading.Timer(.05,self.cancel.set)
        with self.assertRaises(Cancelled),s:
            timer.start();s.pause()
        timer.join();self.assertTrue(s.metrics['process_reaped']);self.assertEqual(s.metrics['stop_reason'],'CANCELLED');self.cancel.clear()
        s=port.PausedOutputSession(self.binding('hang'),self.context,self.root/'out-deadline',self.cancel,time.monotonic()+1.1)
        with self.assertRaises(Limits),s:s.pause()
        self.assertTrue(s.metrics['process_reaped']);self.assertEqual(s.metrics['resume_commands_sent'],0);self.assertEqual(s.metrics['stop_reason'],'DEADLINE')
    def test_measured_resource_limit_reaps_actual_child(self):
        s=self.session('hang',rss_limit_bytes=1)
        with self.assertRaises(Limits),s:s.pause()
        self.assertTrue(s.metrics['process_reaped']);self.assertEqual(s.metrics['stop_reason'],'RSS_LIMIT')
    def test_mutated_feature_or_token_file_refused_without_resume(self):
        for name in ('features_path','token_path'):
            with self.subTest(name=name):
                s=port.PausedOutputSession(self.binding(),self.context,self.root/('out-'+name),self.cancel,time.monotonic()+5)
                with self.assertRaises(Unavailable),s:
                    s.pause();getattr(s,name).write_text('{}');s.resume([])
                self.assertTrue(s.metrics['process_reaped']);self.assertEqual(s.metrics['resume_commands_sent'],0)
    def test_old_head_and_wrong_live_abi_are_not_silently_reused(self):
        binding=self.binding();abi=binding['feature_abi'];observed={'feature':[1.]+[0.]*1023,'feature_abi':abi}
        p=self.root/'head.npz';np.savez(p,format='c3-native-first-token-delta-v2')
        with self.assertRaisesRegex(Unavailable,'Old separate'):port.infer_live_head(observed,p,file_hash(p),abi)
        self.head(p,dict(abi,n_batch=512))
        with self.assertRaisesRegex(Unavailable,'different causal'):port.infer_live_head(observed,p,file_hash(p),abi)
    def head(self,path,abi):
        anchor=np.zeros((1,1024));anchor[0,0]=1;w=np.zeros((1025,1));w[0,0]=2.
        np.savez(path,format=port.HEAD_FORMAT,feature_abi=dumps(abi),token_ids=np.array([7]),weights=w,anchors=anchor,
                 temperature=1.,max_bias=12.,support_cosine=.95,feature_offset=np.zeros(1024),feature_scale=np.ones(1024))
    def test_live_head_bound_bias_and_out_of_support_with_no_approval(self):
        abi=self.binding()['feature_abi'];p=self.root/'head.npz';self.head(p,abi)
        observed={'feature':[1.]+[0.]*1023,'feature_abi':abi}
        predicted=port.infer_live_head(observed,p,file_hash(p),abi)
        self.assertEqual(predicted['first_token_bias'],[[7,2.]]);self.assertEqual(predicted['approval_authority'],0)
        observed['feature']=[0.,1.]+[0.]*1022
        self.assertEqual(port.infer_live_head(observed,p,file_hash(p),abi)['first_token_bias'],[])
        with self.assertRaises(Unavailable):port.infer_live_head(observed,p,'0'*64,abi)
    def test_protocol_bounds_and_duplicate_json_keys(self):
        for rows in ([[True,1.]],[[0,True]],[[0,float('nan')]],[[0,12.1]],[[0,1.],[0,2.]],[[65536,1.]],[[i,1.] for i in range(17)]):
            with self.subTest(rows=rows),self.assertRaises(Unavailable):port.bias_rows(rows)
        with self.assertRaises(Unavailable):port.unique_json('{"nonce":1,"nonce":2}')
        with self.assertRaises(Unavailable):port.unique_json('{"value":NaN}')
    def test_binding_change_and_trimmed_context_rejected_before_child(self):
        binding=self.binding();Path(binding['identity']['model_path']).write_bytes(b'changed')
        s=port.PausedOutputSession(binding,self.context,self.root/'out-mutated-model',self.cancel,time.monotonic()+5)
        with self.assertRaises(Unavailable),s:pass
        self.assertIsNone(s.proc)
        with self.assertRaises(Unavailable):port.PausedOutputSession(self.binding(),dict(self.context,history_trimmed=True),self.root/'out-trimmed',self.cancel,time.monotonic()+5)
    def test_actual_dladdr_alias_resolves_pinned_sha_and_wrong_target_rejects(self):
        identity=self.binding()['identity'];pins=identity['libraries'];loaded=[]
        for name,sha in pins.items():
            alias=Path(name+'.0');alias.symlink_to(Path(name).name)
            loaded.append({'path':str(alias),'sha256':sha})
        self.assertTrue(port.loaded_library_pins_match(loaded,pins))
        wrong=self.root/'untrusted-library.so';wrong.write_bytes(b'wrong library bytes')
        alias=Path(loaded[0]['path']);alias.unlink();alias.symlink_to(wrong.name)
        self.assertFalse(port.loaded_library_pins_match(loaded,pins))
        alias.unlink();alias.symlink_to(Path(next(iter(pins))).name)
        loaded[0]['sha256']='0'*64
        self.assertFalse(port.loaded_library_pins_match(loaded,pins))

if __name__=='__main__':unittest.main()
