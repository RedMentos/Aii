"""Software seams only: native stream/model correctness has separate proofs."""
import json
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch
from v13.common import Cancelled,Limits,Unavailable
from v13.config import DEFAULTS,validate
from v13.runners import CausalStreamRunner,RunnerPool,LlamaRunner
from v13.runtime import Runtime
from v13.operator import Operator

class Template:
    def __init__(self,*args):self.binary=None;self.reaped=False;self.ids=[1,2]
    def load(self,*args):pass
    def pids(self):return []
    def unload(self):self.reaped=True;return {'process_reaped':True}
    def _json(self,method,path,payload,deadline):
        if path=='/apply-template':return {'prompt':'exact template'}
        return {'tokens':self.ids}

class Session:
    failure=None
    def __init__(self,binding,context,out,cancel,deadline,**kwargs):
        self.context=context;self.proc=None;self.rows=None;self.metrics={'process_reaped':False}
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
    def close(self):self.metrics['process_reaped']=True
    def pause(self):return {'native_context_binding':{'scope':'EXACT_SAME_CAUSAL_PREFILL','live_generation_kv_tap':True}}
    def resume(self,rows):
        self.rows=rows
        yield {'event':'TOKEN','text':'Hal'}
        if self.failure:raise self.failure
        yield {'event':'TOKEN','text':'lo!'}
        yield {'event':'COMPLETE','native_token_ids':[10,11], 'raw_result':{'stop_reason':'TOKEN_LIMIT','resume_prefill_calls':0,'resume_decode_calls':1,'unbiased_continuation_steps':1,'same_context_lifetime':True}}

class CausalRunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.model=self.home/'actual.gguf'
        self.runner=CausalStreamRunner(self.home,self.model,dict(DEFAULTS,answer_tokens=64))
        self.binding={'feature_abi':{'stream_abi':'TEST_SOFTWARE'},'identity':{'model_path':str(self.model),'server_path':'/exact/pinned/server'}}
        self.template=Template();self.active=None;Session.failure=None
    def tearDown(self):self.tmp.cleanup()
    def generate(self,**kwargs):
        def make_session(*args,**kw):
            self.assertTrue(self.template.reaped,'template must reap before stream starts')
            self.assertEqual(self.template.binary,'/exact/pinned/server')
            self.active=Session(*args,**kw);return self.active
        with patch('v13.causal_prepare.check_prepared',return_value=self.binding),patch('scripts.native_prefill_stream_client.StreamingOutputSession',side_effect=make_session),patch('v13.runners.LlamaRunner',return_value=self.template):
            return list(self.runner.generate([{'role':'user','content':'Real query'}],threading.Event(),time.monotonic()+10,**kwargs))
    def test_full_stream_uses_zero_bias_and_preserves_actual_context(self):
        self.assertEqual(self.generate(),['Hal','lo!']);self.assertEqual(self.active.rows,[])
        self.assertEqual(self.active.context['messages'],[{'role':'user','content':'Real query'}])
        self.assertFalse(self.active.context['history_trimmed'])
        self.assertTrue(self.runner.last_metrics['process_reaped']);self.assertEqual(self.runner.last_metrics['resume_prefill_calls'],0)
        self.assertEqual(self.runner.last_metrics['sampling'],'NATIVE_GREEDY')
    def test_old_bias_and_schema_refused_before_native_start(self):
        for kw in ({'first_token_bias':[[10,1.]]},{'schema':{}}):
            with self.subTest(kw=kw),self.assertRaises(Unavailable):self.generate(**kw)
            self.assertIsNone(self.active)
    def test_long_context_refused_without_silent_history_trimming(self):
        self.template.ids=list(range(513))
        with self.assertRaises(Limits):self.generate()
        self.assertTrue(self.template.reaped);self.assertIsNone(self.active)
    def test_approved_callback_at_checked_pause_preserves_zero_mode(self):
        self.runner.cfg['c3_decode_mode']='same_causal';calls=[]
        def provider(observed):
            calls.append(observed)
            return {'fallback_reason':'APPROVED_SAME_CAUSAL_FIRST_TOKEN_DELTA','prediction':{'individually_approved':True,'approved_update_id':'SOFTWARE_TEST_UPDATE','in_support':True,'first_token_bias':[[10,1.]],'nearest_native_cosine':1.}}
        self.runner.bias_provider=provider
        self.assertEqual(self.generate(),['Hal','lo!']);self.assertEqual(len(calls),1);self.assertEqual(self.active.rows,[[10,1.]])
        from v13.common import file_hash
        self.assertEqual(self.runner.last_metrics['observed_sha256'],file_hash(Path(self.runner.last_metrics['artifact_directory'])/'observed.json'))
        self.assertTrue(self.runner.last_metrics['learned_first_token_delta_applied'])
        self.runner.cfg['c3_decode_mode']='same_causal_zero';self.generate();self.assertEqual(len(calls),1);self.assertEqual(self.active.rows,[])
    def test_absent_revoked_or_unsupported_callback_keeps_zero_resume(self):
        self.runner.cfg['c3_decode_mode']='same_causal'
        self.runner.bias_provider=lambda observed:{'fallback_reason':'REVOKED_SOURCE','prediction':None}
        self.generate();self.assertEqual(self.active.rows,[]);self.assertFalse(self.runner.last_metrics['learned_head_loaded'])
        self.runner.bias_provider=lambda observed:{'fallback_reason':'OUT_OF_SUPPORT','prediction':{'individually_approved':True,'approved_update_id':'SOFTWARE_TEST_UPDATE','in_support':False,'first_token_bias':[],'nearest_native_cosine':0.}}
        self.generate();self.assertEqual(self.active.rows,[]);self.assertFalse(self.runner.last_metrics['learned_first_token_delta_applied'])
    def test_unapproved_callback_cannot_supply_delta(self):
        self.runner.cfg['c3_decode_mode']='same_causal'
        self.runner.bias_provider=lambda observed:{'fallback_reason':'FAKE','prediction':{'in_support':True,'first_token_bias':[[10,1.]]}}
        with self.assertRaises(Unavailable):self.generate()
        self.assertTrue(self.runner.last_metrics['process_reaped'])
    def test_template_transport_error_after_cancel_keeps_cancel_semantics(self):
        cancel=threading.Event()
        def fail(*args):cancel.set();raise OSError('Transport closed')
        self.template.load=fail
        with patch('v13.causal_prepare.check_prepared',return_value=self.binding),patch('v13.runners.LlamaRunner',return_value=self.template):
            with self.assertRaises(Cancelled):list(self.runner.generate([{'role':'user','content':'Q'}],cancel,time.monotonic()+10))
        self.assertTrue(self.template.reaped);self.assertEqual(self.runner.last_metrics['status'],'CANCELLED')
    def test_non_supported_decode_cap_refused(self):
        with self.assertRaises(Unavailable):self.generate(max_tokens=256)
        self.assertIsNone(self.active)
    def test_interrupted_partial_text_yielded_and_process_reaped(self):
        Session.failure=Cancelled('test cancellation');tokens=[]
        with patch('v13.causal_prepare.check_prepared',return_value=self.binding),patch('scripts.native_prefill_stream_client.StreamingOutputSession',side_effect=Session),patch('v13.runners.LlamaRunner',return_value=self.template):
            with self.assertRaises(Cancelled):
                for token in self.runner.generate([{'role':'user','content':'Q'}],threading.Event(),time.monotonic()+10):tokens.append(token)
        self.assertEqual(tokens,['Hal']);self.assertTrue(self.runner.last_metrics['process_reaped']);self.assertEqual(self.runner.last_metrics['status'],'CANCELLED')
    def test_pool_preserves_default_generate_and_tap_and_optin_output_only(self):
        pool=RunnerPool(self.home,SimpleNamespace(path_for=lambda role:self.model),dict(DEFAULTS))
        self.assertIsInstance(pool.get_output('C3_LANGUAGE'),LlamaRunner)
        pool.cfg['c3_decode_mode']='same_causal_zero';self.assertIsInstance(pool.get_output('C3_LANGUAGE'),CausalStreamRunner)
        self.assertIsInstance(pool.get('C3_LANGUAGE'),LlamaRunner)
    def test_retention_only_prunes_completed_own_nonce_dirs(self):
        tmp=self.home/'tmp';tmp.mkdir()
        for i in range(11):
            d=tmp/('c3-causal-stream-'+format(i,'032x'));d.mkdir()
            (d/'controller.json').write_text(json.dumps({'status':'SAME_CONTEXT_STREAM_COMPLETE','process_reaped':True,'pid':1}))
        active=tmp/('c3-causal-stream-'+'f'*32);active.mkdir()
        (active/'controller.json').write_text(json.dumps({'status':'WAITING_READY','process_reaped':False,'pid':1}))
        unrelated=tmp/'unrelated';unrelated.mkdir();(unrelated/'important').write_text('keep')
        link=tmp/('c3-causal-stream-'+'e'*32);link.symlink_to(unrelated,target_is_directory=True)
        self.assertEqual(len(self.runner.prune_completed()),3)
        self.assertTrue(active.exists());self.assertTrue((unrelated/'important').exists());self.assertTrue(link.is_symlink())
        self.assertEqual(len([x for x in tmp.iterdir() if x.is_dir() and not x.is_symlink() and x!=active and x!=unrelated]),8)
    def test_configuration_requires_supported_causal_output_limit(self):
        with self.assertRaises(ValueError):validate(dict(DEFAULTS,c3_decode_mode='same_causal_zero'))
        self.assertEqual(validate(dict(DEFAULTS,c3_decode_mode='same_causal_zero',answer_tokens=64))['answer_tokens'],64)
    def test_configuration_rejects_unknown_decode_mode(self):
        with self.assertRaises(ValueError):validate(dict(DEFAULTS,c3_decode_mode='made_up'))

class CausalCoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name))
        self.r.cfg.update(observer_mode='off',c3_decode_mode='same_causal_zero',answer_tokens=64)
        self.r._route=Mock(return_value=('simple',{'source':'SOFTWARE_TEST_SEAM'}))
        self.r.learner.output_delta=Mock(side_effect=AssertionError('Old separate-prefill feature call'))
        self.runner=SimpleNamespace(role='C3_LANGUAGE',last_metrics={'software_test_seam':True},generate=lambda *a,**k:iter(['Hallo!']))
        self.r.pool.get=Mock(return_value=self.runner);self.r.pool.get_output=Mock(return_value=self.runner)
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def wait(self):
        end=time.monotonic()+5
        while not self.r.idle() and time.monotonic()<end:time.sleep(.005)
        self.assertTrue(self.r.idle());return self.r.last_answer()
    def test_optin_coordinator_stream_commits_feedback_context_without_old_head(self):
        eid=self.r.submit('Hallo');row=self.wait();self.assertEqual((row['status'],row['text']),('FINAL','Hallo!'))
        meta=json.loads(row['metadata']);self.assertTrue(meta['model_generated'])
        self.assertEqual(meta['output_adapter_status'],'UNAVAILABLE_NO_APPROVED_SAME_CAUSAL_HEAD')
        self.r.learner.output_delta.assert_not_called();self.r.pool.get_output.assert_called_once_with('C3_LANGUAGE')
        context=json.loads(self.r.store.one("SELECT payload FROM packets WHERE kind='OutputAdapterContext' AND event_id=?",(eid,))['payload'])
        self.assertEqual(json.loads(self.r.store.read_source(context['context_ref']))[-1],{'role':'user','content':'Hallo'})
        self.r.learner.output_feedback(eid,'Explizite Testreferenz','learn')
        self.assertEqual(self.r.learner.output_labels()[0][0]['value'],'Explizite Testreferenz')
    def test_approved_exact_rule_bypasses_optin_decoder(self):
        op=Operator(self.r);rid=op.run(':rules fixed "Regel?" "Fest."').split(';')[0];op.run(':approve '+rid)
        self.r.submit('Regel?');row=self.wait();self.assertEqual(row['text'],'Fest.')
        self.r.pool.get_output.assert_not_called();self.r.learner.output_delta.assert_not_called()
        self.assertEqual(json.loads(row['metadata'])['output_authority'],'APPROVED_FIXED_RULE')
    def test_partial_native_interruption_commits_partial_and_honest_status(self):
        def stream(*args,**kwargs):
            yield 'Teilantwort';raise Cancelled('Software interruption seam')
        self.runner.generate=stream
        self.r.submit('Hallo');row=self.wait();self.assertEqual((row['text'],row['status']),('Teilantwort','CANCELLED'))
        self.assertTrue(json.loads(row['metadata'])['model_generated'])

if __name__=='__main__':unittest.main()
