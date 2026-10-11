"""Offline isolated candidate regressions; fixture counters are not native proof."""
import copy
import json
import os
import sys
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.native_firing_runtime_candidate import load_candidate, sources
from tests import test_sparse_delivery as delivery_tests
from tests import test_sparse_runner_lifecycle as lifecycle_tests
from tests import test_sparse_delivery_runtime as runtime_tests
from v13.common import Cancelled, Unavailable, file_hash
from v13.sparse_audit import PREFIX, SCHEMA


def record(event, **fields):
    return PREFIX+json.dumps(dict(schema=SCHEMA,event=event,**fields))+'\n'


def log_window(count=1):
    return record('begin',request=9,slots=1,layer=7)+record('batch',request=9,
        rows=2,batches=1,applied=[count],guard_blocked=[0])


def audit(binding, count=1):
    return dict(status='OBSERVED_NATIVE_WRITES',request=9,layer=7,evaluated_rows=2,
        batches=1,slot_applied_counts=[count],slot_guard_blocked_counts=[0],
        fired_rows=[0] if count else [],exact_retained=True,quality_proven=False,
        activation_authorized=False,semantic_truth_authority=False,
        request_status='FINAL',loaded_binding=copy.deepcopy(binding))


class FiringRowMap(unittest.TestCase):
    setUp=delivery_tests.SparseDelivery.setUp
    tearDown=delivery_tests.SparseDelivery.tearDown
    make_native=delivery_tests.SparseDelivery.make_native
    activate=delivery_tests.SparseDelivery.activate
    edit_side=delivery_tests.SparseDelivery.edit_side

    def observed(self, a=None, binding=None, memories=None):
        from v13.memory_server import captured_delivery_binding
        if binding is None:binding=captured_delivery_binding(self.home,'C3_LANGUAGE',self.model)
        return load_candidate('memory_server').observed_shadow_delivery(self.s,self.home,
            'C3_LANGUAGE',self.model,binding,[self.memory] if memories is None else memories,
            audit(binding) if a is None else a)

    def test_actual_write_map_is_shadow_only_and_zero_is_observed_zero(self):
        result=self.observed()
        self.assertEqual(result['observed_memory_ids'],[self.mid])
        self.assertEqual(result['observed_provenance'],[self.memory['source_ref']])
        self.assertTrue(result['exact_retained']);self.assertEqual(result['mode'],'SHADOW')
        for key in ('quality_proven','activation_authorized','semantic_truth_authority'):
            self.assertFalse(result[key])
        result=self.observed(a=audit(result['binding'],0))
        self.assertEqual(result['firing'],'OBSERVED_NATIVE_WRITES')
        self.assertEqual(result['observed_memory_ids'],[])

    def test_bound_model_binary_library_sidecar_native_change_fails_closed(self):
        from v13.memory_server import captured_delivery_binding
        for p in (self.model,self.binary,self.path,Path(str(self.path)+'.items.json')):
            binding=captured_delivery_binding(self.home,'C3_LANGUAGE',self.model)
            old=p.read_bytes();p.write_bytes(old+b'x')
            result=self.observed(a=audit(binding),binding=binding)
            self.assertEqual(result['observed_memory_ids'],[]);p.write_bytes(old)
        binding=captured_delivery_binding(self.home,'C3_LANGUAGE',self.model)
        lib=self.binary.parent/'libchanged.so';lib.write_bytes(b'new runtime library')
        self.assertEqual(self.observed(a=audit(binding),binding=binding)['observed_memory_ids'],[])

    def test_forgotten_inactive_deleted_and_source_conflict_never_claim_fact_firing(self):
        self.edit_side(lambda m:m.update(forgotten=[self.mid]));self.activate(self.path,'forgotten')
        self.assertEqual(self.observed()['observed_memory_ids'],[])
        self.edit_side(lambda m:m.update(forgotten=[]));self.activate(self.path,'restored')
        for column in ('active','deleted'):
            if column=='active':
                with self.s.tx() as c:c.execute('UPDATE memories SET active=0 WHERE id=?',(self.mid,))
            else:
                with self.s.tx() as c:
                    c.execute('UPDATE memories SET active=1 WHERE id=?',(self.mid,))
                    c.execute('UPDATE sources SET deleted=1 WHERE id=?',(self.memory['source_id'],))
            self.assertEqual(self.observed()['observed_memory_ids'],[])
        with self.s.tx() as c:c.execute('UPDATE sources SET deleted=0 WHERE id=?',(self.memory['source_id'],))
        for changed in ({'value':'other'},{'source_ref':dict(self.memory['source_ref'],sha256='0'*64)}):
            self.assertEqual(self.observed(memories=[dict(self.memory,**changed)])['observed_memory_ids'],[])

    def test_row_dimensions_status_binding_and_authority_fail_closed(self):
        binding=self.observed()['binding']
        for changed in ({'slot_applied_counts':[True]}, {'slot_applied_counts':[1,0]},
                        {'fired_rows':[]},{'layer':8},{'request_status':'CANCELLED'},
                        {'loaded_binding':{}},{'quality_proven':True}, {'request':True}):
            result=self.observed(a=dict(audit(binding),**changed))
            self.assertEqual(result['observed_memory_ids'],[])
            self.assertEqual(result['firing'],'UNMEASURED')
        result=self.observed(a=dict(audit(binding,2),slot_guard_blocked_counts=[1]))
        self.assertEqual(result['observed_memory_ids'],[])
        self.assertEqual(result['firing_reason'],'INVALID_REQUEST_ROW_MAP')
        for reason in ('NO_EVALUATED_ROWS','NO_PROMPT_MARKER','MULTIPLE_REQUESTS','BAD_JSON'):
            result=self.observed(a={'status':'UNAVAILABLE','reason':reason})
            self.assertEqual(result['firing_reason'],reason)
            self.assertTrue(result['exact_retained'])

    def test_reapproval_or_forget_during_mapping_rechecks_binding(self):
        module=load_candidate('memory_server')
        binding=module.captured_delivery_binding(self.home,'C3_LANGUAGE',self.model)
        with patch.object(module,'captured_delivery_binding',side_effect=[binding,None]):
            result=module.observed_shadow_delivery(self.s,self.home,'C3_LANGUAGE',self.model,
                binding,[self.memory],audit(binding))
        self.assertEqual(result['observed_memory_ids'],[])
        self.assertEqual(result['firing_reason'],'REQUEST_BINDING_CHANGED')
        self.assertEqual(result['firing'],'UNMEASURED')


class FiringRunnerWindow(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name)
        (self.home/'logs').mkdir();(self.home/'config').mkdir();(self.home/'bin').mkdir()
        self.model=self.home/'m.gguf';self.model.write_bytes(b'm')
        self.binding={'path':'fixture','native_sha256':'fixture'}
        self.r=load_candidate('runners').LlamaRunner(self.home,'C3_LANGUAGE',self.model,
            {'native_memory_audit':True,'answer_tokens':4})
        self.r._audit_enabled=True
        self.r._audit_completed=True
        self.log=self.home/'logs/C3_LANGUAGE.log';self.r.log_handle=open(self.log,'ab')
        self.r.proc=SimpleNamespace(pid=os.getpid(),poll=lambda:None)
        self.r._memory_delivery_binding=copy.deepcopy(self.binding)
        self.r._loaded_stamp=self.r._lifecycle_stamp()

    def tearDown(self):
        if self.r.log_handle:self.r.log_handle.close()
        self.tmp.cleanup()

    def write(self, text):
        self.r.log_handle.write(text.encode());self.r.log_handle.flush()

    def test_only_current_request_window_is_reported(self):
        self.write(log_window());self.r._audit_begin_window();self.write(log_window(2))
        observed=self.r._audit_finish_window('FINAL')
        self.assertEqual(observed['slot_applied_counts'],[2])
        self.assertEqual(observed['loaded_binding'],self.binding)
        self.assertFalse(observed['semantic_truth_authority'])

    def test_cancel_changed_binding_cache_malformed_and_ambiguous_fail_closed(self):
        self.r._audit_begin_window();self.write(log_window())
        self.assertEqual(self.r._audit_finish_window('CANCELLED')['reason'],'REQUEST_NOT_FINAL')
        self.r._memory_delivery_binding={}
        self.assertEqual(self.r._audit_finish_window('FINAL')['reason'],'REQUEST_BINDING_CHANGED')
        self.r._memory_delivery_binding=self.binding
        for raw,expected in ((record('begin',request=9,slots=1,layer=7),'NO_EVALUATED_ROWS'),
                             (log_window()*2,'MULTIPLE_REQUESTS'),(PREFIX+'{','Expecting property name')):
            self.r._audit_begin_window();self.write(raw)
            result=self.r._audit_finish_window('FINAL')
            self.assertEqual(result['status'],'UNAVAILABLE')
            self.assertTrue(result['reason'].startswith(expected),result)

    def test_log_rotate_truncate_and_multi_native_steps_fail_closed(self):
        self.write('old bytes');self.r._audit_begin_window()
        self.log.write_bytes(b'')
        self.assertEqual(self.r._audit_finish_window('FINAL')['reason'],'AUDIT_LOG_CHANGED')
        self.r._audit_begin_window();old=self.log.with_suffix('.old');self.log.rename(old)
        self.log.write_text(log_window())
        self.assertEqual(self.r._audit_finish_window('FINAL')['reason'],'AUDIT_LOG_CHANGED')
        self.r._audit_begin_window(multiple_steps=True)
        self.assertEqual(self.r._audit_finish_window('FINAL')['reason'],'MULTIPLE_NATIVE_STEPS')

    def test_metrics_wrap_actual_request_window_and_clear_on_next_request(self):
        def generate(*args):
            self.r._audit_begin_window();self.write(log_window());self.r._audit_completed=True;yield 'fixture'
        self.r._generate=generate
        self.assertEqual(list(self.r.generate([],threading.Event(),time.monotonic()+1)),['fixture'])
        self.assertEqual(self.r.last_metrics['native_memory_firing']['status'],'OBSERVED_NATIVE_WRITES')
        def no_rows(*args):
            self.r._audit_begin_window();self.write(record('begin',request=10,slots=1,layer=7));self.r._audit_completed=True;yield 'cached'
        self.r._generate=no_rows
        list(self.r.generate([],threading.Event(),time.monotonic()+1))
        self.assertEqual(self.r.last_metrics['native_memory_firing']['reason'],'NO_EVALUATED_ROWS')

    def test_eof_without_completion_stop_never_claims_completed_firing(self):
        def generate(*args):
            self.r._audit_begin_window();self.write(log_window());yield 'partial'
        self.r._generate=generate
        list(self.r.generate([],threading.Event(),time.monotonic()+1))
        self.assertEqual(self.r.last_metrics['native_memory_firing']['reason'],'REQUEST_NOT_COMPLETED')

    def test_cancelled_generator_keeps_unavailable_metrics_and_unloads(self):
        def generate(*args):
            self.r._audit_begin_window();self.write(log_window());yield 'partial'
            raise Cancelled('fixture cancelled')
        self.r._generate=generate;unloads=[]
        self.r.unload=lambda:unloads.append(True) or {'process_reaped':True}
        with self.assertRaises(Cancelled):list(self.r.generate([],threading.Event(),time.monotonic()+1))
        self.assertEqual(self.r.last_metrics['status'],'CANCELLED')
        self.assertEqual(self.r.last_metrics['native_memory_firing']['status'],'UNAVAILABLE')
        self.assertEqual(self.r.last_metrics['native_memory_firing']['reason'],'REQUEST_NOT_FINAL')
        self.assertEqual(unloads,[True])

    def test_concurrent_audit_request_is_rejected_and_off_path_adds_no_metrics(self):
        self.r._audit_lock.acquire()
        with self.assertRaises(Unavailable):list(self.r.generate([],threading.Event(),time.monotonic()+1))
        self.r._audit_lock.release()
        self.r.cfg['native_memory_audit']=False;self.r._audit_enabled=False
        self.r._generate=lambda *args:iter(['normal'])
        list(self.r.generate([],threading.Event(),time.monotonic()+1))
        self.assertNotIn('native_memory_firing',self.r.last_metrics)


class AuditLaunch(unittest.TestCase):
    setUp=lifecycle_tests.SparseRunnerLifecycle.setUp
    tearDown=lifecycle_tests.SparseRunnerLifecycle.tearDown
    bind=lifecycle_tests.SparseRunnerLifecycle.bind
    load=lifecycle_tests.SparseRunnerLifecycle.load

    def test_opt_in_only_approved_memory_child_and_toggle_reloads(self):
        cfg={'context_tokens':256,'threads':1,'native_memory_audit':False}
        self.runner=load_candidate('runners').LlamaRunner(self.home,'C3_LANGUAGE',self.model,cfg)
        import subprocess
        with patch.dict(os.environ,{'V13_MEMORY_AUDIT':'1'}),patch('v13.runners.subprocess.Popen',wraps=subprocess.Popen) as launch:
            self.load();self.assertNotIn('V13_MEMORY_AUDIT',launch.call_args.kwargs['env'])
            old=self.runner.proc;cfg['native_memory_audit']=True;self.load()
            self.assertIsNotNone(old.poll());self.assertEqual(launch.call_args.kwargs['env']['V13_MEMORY_AUDIT'],'1')
            (self.home/'config/lora-active.json').write_text('{}');self.load()
            self.assertNotIn('V13_MEMORY_AUDIT',launch.call_args.kwargs['env'])

    def test_real_loopback_http_stream_binds_window_and_terminal_stop(self):
        script='#!'+sys.executable+'''\nimport json,os,sys
from http.server import BaseHTTPRequestHandler,HTTPServer
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        self.send_response(200);self.end_headers();self.wfile.write(b'{"status":"ok"}')
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.send_response(200);self.end_headers()
        if self.path=='/apply-template':self.wfile.write(b'{"prompt":"test"}')
        elif self.path=='/tokenize':self.wfile.write(b'{"tokens":[1,2]}')
        elif self.path=='/completion':
            if os.environ.get('V13_MEMORY_AUDIT')=='1':
                for event,fields in [('begin',dict(request=1,slots=1,layer=7)),
                                     ('batch',dict(request=1,rows=2,batches=1,applied=[1],guard_blocked=[0]))]:
                    sys.stderr.write('V13_MEMORY_AUDIT '+json.dumps(dict(schema='v13-native-firing-v1',event=event,**fields))+'\\n')
                sys.stderr.flush()
            self.wfile.write(b'data: {"content":"fixture","tokens":[7],"stop":true}\\n\\n')
HTTPServer(('127.0.0.1',int(sys.argv[sys.argv.index('--port')+1])),Handler).serve_forever()
'''
        self.binary.write_text(script);self.binary.chmod(0o755)
        (self.home/'config/memory-server.json').write_text(json.dumps({'binary_sha256':file_hash(self.binary)}))
        cfg={'context_tokens':256,'threads':1,'answer_tokens':4,'temperature':.1,'native_memory_audit':True}
        self.runner=load_candidate('runners').LlamaRunner(self.home,'C3_LANGUAGE',self.model,cfg)
        tokens=list(self.runner.generate([{'role':'user','content':'software fixture'}],self.cancel,time.monotonic()+5))
        self.assertEqual(tokens,['fixture'])
        measured=self.runner.last_metrics['native_memory_firing']
        self.assertEqual(measured['status'],'OBSERVED_NATIVE_WRITES')
        self.assertEqual(measured['request_status'],'FINAL')
        self.assertEqual(measured['loaded_binding'],self.runner.memory_delivery_binding)
        self.assertFalse(measured['activation_authorized'])
        self.assertFalse(measured['semantic_truth_authority'])


class FiringRuntimeShadow(unittest.TestCase):
    setUp=runtime_tests.SparseDeliveryRuntime.setUp
    tearDown=runtime_tests.SparseDeliveryRuntime.tearDown
    runner_fixture=runtime_tests.SparseDeliveryRuntime.runner_fixture
    turn=runtime_tests.SparseDeliveryRuntime.turn

    def test_candidate_persists_observation_without_removing_exact_sources(self):
        candidate=load_candidate('runtime');self.r.__class__=candidate.Runtime
        self.runner.last_metrics['native_memory_firing']=audit(self.binding)
        memory=load_candidate('memory_server')
        store=load_candidate('store')
        with patch('v13.memory_server.observed_shadow_delivery',memory.observed_shadow_delivery,create=True),patch('v13.store.telemetry_metrics',store.telemetry_metrics):
            event,row,meta=self.turn()
        delivery=meta['sparse_delivery_shadow']
        self.assertEqual(delivery['observed_memory_ids'],[self.mid])
        self.assertTrue(delivery['exact_retained']);self.assertEqual(delivery['mode'],'SHADOW')
        stored=self.r.store.one("SELECT metrics FROM telemetry WHERE kind='sparse_delivery_shadow' AND event_id=?",(event,))
        payload=json.loads(stored['metrics'])
        self.assertEqual(payload['observed_memory_ids'],[self.mid])
        self.assertNotIn('Mitzi',stored['metrics'])
        self.assertFalse(payload['semantic_truth_authority'])

    def test_candidate_hash_bound_sources_remain_unmodified(self):
        original,changed=sources()
        self.assertNotEqual(original,changed)
        actual={name:(Path(__file__).parents[1]/name).read_text() for name in original}
        self.assertTrue(actual==original or actual==changed)


if __name__=='__main__':unittest.main()
