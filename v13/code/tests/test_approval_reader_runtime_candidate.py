"""Isolated reader synchronization with real SQLite and loopback child processes.

Authored adapter bytes only; no native model training/utility claim.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import patch

from scripts.approval_reader_runtime_candidate import load_candidate,sources
from tests import test_weight_approval_atomic as approval_tests
from tests import test_sparse_runner_lifecycle as lifecycle_tests
from v13.common import Cancelled,Unavailable,file_hash
from v13.lora_trainer import AdapterRegistry,REGISTRY_KEY
from v13.store import Store


def server(home):
    path=home/'bin/llama-server';path.parent.mkdir(exist_ok=True)
    path.write_text('#!'+sys.executable+'''\nimport sys
from http.server import BaseHTTPRequestHandler,HTTPServer
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        self.send_response(200);self.end_headers();self.wfile.write(b'{"status":"ok"}')
HTTPServer(('127.0.0.1',int(sys.argv[sys.argv.index('--port')+1])),Handler).serve_forever()
''');path.chmod(0o755)


class ApprovalReader(unittest.TestCase):
    setUp=approval_tests.ApprovalAtomicity.setUp
    tearDown=approval_tests.ApprovalAtomicity.tearDown
    restart=approval_tests.ApprovalAtomicity.restart
    assert_pending=approval_tests.ApprovalAtomicity.assert_pending
    def make_runner(self):
        server(self.home)
        return load_candidate('runners').LlamaRunner(self.home,'C3_LANGUAGE',self.model,
            {'context_tokens':256,'threads':1},approval_store=self.s)
    def test_real_commit_failure_reader_waits_and_never_launches_attempted_adapter(self):
        with self.s.tx() as c:
            c.execute('CREATE TABLE candidate_parent(id INTEGER PRIMARY KEY)')
            c.execute('CREATE TABLE candidate_child(parent INTEGER REFERENCES candidate_parent(id) DEFERRABLE INITIALLY DEFERRED)')
            c.execute("CREATE TRIGGER candidate_fail AFTER UPDATE OF status ON requests WHEN NEW.status='APPROVED' BEGIN INSERT INTO candidate_child VALUES (123); END")
        self.coordinated_read(success=False)
        self.assert_pending();self.restart();self.assert_pending()
    def test_success_reader_waits_then_launches_committed_snapshot_and_restart_matches(self):
        self.coordinated_read(success=True)
        self.restart();self.assertEqual(self.w.batch(self.bid)['status'],'APPROVED')
        runner=self.make_runner()
        try:
            runner.load(threading.Event(),time.monotonic()+5)
            self.assertEqual(Path(runner._launch_assets['adapter']).read_bytes(),self.adapter.read_bytes())
        finally:runner.unload()
    def coordinated_read(self,success):
        runner=self.make_runner();published=threading.Event();proceed=threading.Event();reader_entered=threading.Event();reader_done=threading.Event();errors=[];commands=[]
        publish=self.w._publish_adapter_mirror;real_popen=subprocess.Popen
        def pause(registry):
            publish(registry)
            if registry.get('active',{}).get('C3_LANGUAGE',{}).get('batch_id')==self.bid:
                published.set()
                if not proceed.wait(4):raise RuntimeError('test timeout')
        def approve():
            try:self.w.approve(self.bid)
            except Exception as exc:errors.append(('approve',type(exc).__name__))
        def read():
            reader_entered.set()
            try:runner.load(threading.Event(),time.monotonic()+6)
            except Exception as exc:errors.append(('read',type(exc).__name__))
            finally:reader_done.set()
        def popen(cmd,*a,**kw):commands.append(list(cmd));return real_popen(cmd,*a,**kw)
        with patch.object(self.w,'_publish_adapter_mirror',pause),patch('subprocess.Popen',side_effect=popen):
            writer=threading.Thread(target=approve);writer.start();reader=None
            try:
                self.assertTrue(published.wait(3));reader=threading.Thread(target=read);reader.start()
                self.assertTrue(reader_entered.wait(2));self.assertFalse(reader_done.wait(.08));self.assertEqual(commands,[])
            finally:
                proceed.set();writer.join(5)
                if reader:reader.join(7)
        try:
            self.assertFalse(writer.is_alive());self.assertFalse(reader.is_alive());self.assertEqual(len(commands),1)
            self.assertEqual([e for e in errors if e[0]=='read'],[])
            self.assertEqual('--lora-scaled' in commands[0],success)
            if success:
                self.assertEqual(errors,[]);snapshot=Path(commands[0][commands[0].index('--lora-scaled')+1])
                self.assertNotEqual(snapshot,self.adapter);self.assertEqual(snapshot.read_bytes(),self.adapter.read_bytes())
            else:self.assertEqual(errors,[('approve','IntegrityError')])
        finally:runner.unload()
    def test_failed_mirror_recovery_mismatch_fails_closed_before_any_child(self):
        # Real committed database remains unchanged while this authored mirror
        # deliberately models an interrupted/failed-recovery publication.
        runner=self.make_runner();mirror=self.home/'config/lora-active.json'
        mirror.write_text(json.dumps({'C3_LANGUAGE':{'path':str(self.adapter),'sha256':file_hash(self.adapter),'base_model_sha256':file_hash(self.model),'scale':1.,'batch_id':self.bid}}))
        with patch('subprocess.Popen') as launch:
            with self.assertRaisesRegex(Unavailable,'committed approval'):runner.load(threading.Event(),time.monotonic()+4)
            launch.assert_not_called()
        self.assertIsNone(runner.log_handle);self.assertIsNone(runner._asset_snapshot)
    def test_private_snapshot_survives_original_path_replacement_before_child_opens(self):
        self.w.approve(self.bid);runner=self.make_runner();original=self.adapter.read_bytes();read_bytes=[];real_popen=subprocess.Popen
        def replace_then_spawn(cmd,*a,**kw):
            p=Path(cmd[cmd.index('--lora-scaled')+1]);self.adapter.write_bytes(b'changed after snapshot')
            read_bytes.append(p.read_bytes());return real_popen(cmd,*a,**kw)
        try:
            with patch('subprocess.Popen',side_effect=replace_then_spawn):
                # Model load is a loopback authored fixture. Changed originals
                # invalidate the handoff rather than claiming a current binding.
                with self.assertRaises(Unavailable):runner.load(threading.Event(),time.monotonic()+5)
            self.assertEqual(read_bytes,[original]);self.assertIsNone(runner.proc);self.assertIsNone(runner._asset_snapshot)
        finally:self.adapter.write_bytes(original);runner.unload()
    def test_store_lock_is_free_during_popen_and_health_polling(self):
        self.w.approve(self.bid);runner=self.make_runner();real_popen=subprocess.Popen;real_json=runner._json;observed=[]
        def can_take_lock(stage):
            result=[]
            def acquire():
                got=self.s.mutex.acquire(timeout=.3);result.append(got)
                if got:self.s.mutex.release()
            thread=threading.Thread(target=acquire);thread.start();thread.join(1);self.assertEqual(result,[True]);observed.append(stage)
        def spawn(*a,**kw):can_take_lock('popen');return real_popen(*a,**kw)
        def health(*a,**kw):can_take_lock('health');return real_json(*a,**kw)
        try:
            with patch('subprocess.Popen',side_effect=spawn),patch.object(runner,'_json',side_effect=health):runner.load(threading.Event(),time.monotonic()+5)
            self.assertIn('popen',observed);self.assertIn('health',observed)
        finally:runner.unload()
    def test_cancellation_while_waiting_for_approval_never_starts_child(self):
        runner=self.make_runner();ready=threading.Event();cancel=threading.Event();errors=[];guard=runner._approval_guard
        def announce(*args):ready.set();return guard(*args)
        def load():
            try:runner.load(cancel,time.monotonic()+5)
            except Exception as exc:errors.append(type(exc).__name__)
        with patch.object(runner,'_approval_guard',side_effect=announce),patch('subprocess.Popen') as launch:
            with self.s.mutex:
                worker=threading.Thread(target=load);worker.start();self.assertTrue(ready.wait(2));cancel.set()
            worker.join(3);self.assertFalse(worker.is_alive());launch.assert_not_called()
        self.assertEqual(errors,['Cancelled']);self.assertIsNone(runner.log_handle);self.assertIsNone(runner._asset_snapshot)
    def test_cancellation_returns_while_live_approval_writer_still_holds_lock(self):
        self.waiting_reader_interrupt(cancelled=True)
    def test_deadline_returns_while_live_approval_writer_still_holds_lock(self):
        self.waiting_reader_interrupt(cancelled=False)
    def waiting_reader_interrupt(self,cancelled):
        # The approval writer remains paused inside its real SQLite write
        # transaction until the reader has returned. Releasing the mutex
        # before joining the reader would fail to test cancellation latency.
        runner=self.make_runner();published=threading.Event();proceed=threading.Event()
        reader_entered=threading.Event();reader_done=threading.Event();cancel=threading.Event()
        errors=[];writer_errors=[];publish=self.w._publish_adapter_mirror;guard=runner._approval_guard
        def pause(registry):
            publish(registry)
            if registry.get('active',{}).get('C3_LANGUAGE',{}).get('batch_id')==self.bid:
                published.set()
                if not proceed.wait(4):raise RuntimeError('test writer coordination timeout')
        def approve():
            try:self.w.approve(self.bid)
            except BaseException as exc:writer_errors.append(type(exc).__name__)
        def announce(*args):reader_entered.set();return guard(*args)
        def read():
            try:runner.load(cancel,time.monotonic()+(4 if cancelled else .2))
            except BaseException as exc:errors.append(type(exc).__name__)
            finally:reader_done.set()
        writer=None;reader=None
        with patch.object(self.w,'_publish_adapter_mirror',pause),\
             patch.object(runner,'_approval_guard',side_effect=announce),patch('subprocess.Popen') as launch:
            try:
                writer=threading.Thread(target=approve);writer.start();self.assertTrue(published.wait(2))
                reader=threading.Thread(target=read);reader.start();self.assertTrue(reader_entered.wait(1))
                if cancelled:cancel.set()
                self.assertTrue(reader_done.wait(1),'Reader must return before the approval writer releases its lock')
                self.assertTrue(writer.is_alive());self.assertFalse(proceed.is_set())
                launch.assert_not_called();self.assertIsNone(runner.proc)
                self.assertIsNone(runner.log_handle);self.assertIsNone(runner._asset_snapshot)
            finally:
                proceed.set()
                if writer:writer.join(4)
                if reader:reader.join(4)
                runner.unload()
        self.assertFalse(writer.is_alive());self.assertFalse(reader.is_alive())
        self.assertEqual(writer_errors,[]);self.assertEqual(errors,['Cancelled' if cancelled else 'Limits'])
        self.assertEqual(self.w.batch(self.bid)['status'],'APPROVED')
    def test_copy_hash_mismatch_never_launches_and_cleans_snapshot(self):
        import shutil
        self.w.approve(self.bid);runner=self.make_runner();copyfile=shutil.copyfile
        def corrupt(src,dest):
            result=copyfile(src,dest);Path(dest).write_bytes(b'corrupt copy fixture');return result
        with patch('shutil.copyfile',side_effect=corrupt),patch('subprocess.Popen') as launch:
            with self.assertRaisesRegex(Unavailable,'during snapshot'):runner.load(threading.Event(),time.monotonic()+4)
            launch.assert_not_called()
        self.assertIsNone(runner._asset_snapshot);self.assertIsNone(runner.log_handle)
    def test_runtime_injects_shared_store_and_pool_causal_template_inherits_it(self):
        module=load_candidate('runtime');runners=load_candidate('runners');module.RunnerPool=runners.RunnerPool
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            runtime=module.Runtime(Path(tmp))
            try:self.assertIs(runtime.pool.approval_store,runtime.store)
            finally:runtime.close()
        class Models:
            def path_for(self,role):return self.model
        models=Models();models.model=self.model
        pool=runners.RunnerPool(self.home,models,{'c3_decode_mode':'same_causal'},approval_store=self.s)
        causal=pool.get_output('C3_LANGUAGE');self.assertIs(causal.approval_store,self.s)
        self.assertIs(pool.get('C3_LANGUAGE').approval_store,self.s)
        observed=[]
        class Template:
            def __init__(inner,*a,approval_store=None,**kw):observed.append(approval_store)
            def load(inner,*a):raise Unavailable('fixture stops before model inference')
            def unload(inner):return {'process_reaped':True}
        causal.cfg.update(answer_tokens=64,temperature=0.)
        binding={'identity':{'model_path':str(self.model),'server_path':str(self.home/'bin/llama-server')},'feature_abi':'authored-fixture'}
        with patch('v13.causal_prepare.check_prepared',return_value=binding),patch.object(runners,'LlamaRunner',Template):
            with self.assertRaisesRegex(Unavailable,'fixture stops'):list(causal.generate([],threading.Event(),time.monotonic()+3))
        self.assertEqual(observed,[self.s])


class SparseSnapshot(unittest.TestCase):
    bind=lifecycle_tests.SparseRunnerLifecycle.bind
    setUp=lifecycle_tests.SparseRunnerLifecycle.setUp
    tearDown=lifecycle_tests.SparseRunnerLifecycle.tearDown
    def test_memory_snapshot_keeps_approved_original_binding_and_cleans_all_files(self):
        from v13.config import initialize
        initialize(self.home)
        store=Store(self.home)
        cur=self.cur|{'scale':1.}
        store.set_state(REGISTRY_KEY,{'active':{'C3_LANGUAGE#sparse_memory':cur},'history':[]})
        (self.home/'config/lora-active.json').write_text(json.dumps({'C3_LANGUAGE#sparse_memory':cur}))
        self.runner=load_candidate('runners').LlamaRunner(self.home,'C3_LANGUAGE',self.model,
            {'context_tokens':256,'threads':1},approval_store=store)
        real_popen=subprocess.Popen;actual_env=[]
        def capture(cmd,*a,**kw):actual_env.append(kw['env']['V13_MEMORY_FILE']);return real_popen(cmd,*a,**kw)
        try:
            with patch('subprocess.Popen',side_effect=capture):self.runner.load(threading.Event(),time.monotonic()+5)
            snap=Path(actual_env[0]);folder=self.runner._asset_snapshot
            self.assertNotEqual(snap,self.native);self.assertEqual(snap.read_bytes(),self.native.read_bytes())
            self.assertEqual(Path(str(snap)+'.items.json').read_bytes(),self.side.read_bytes())
            self.assertEqual(self.runner.memory_delivery_binding['path'],str(self.native))
            self.assertEqual(self.runner.memory_delivery_binding['native_sha256'],file_hash(snap))
            self.runner.unload();self.assertFalse(folder.exists())
        finally:self.runner.unload();store.close()


if __name__=='__main__':unittest.main()
