"""Real child/loopback lifecycle tests. No model inference or sparse-firing claims."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from v13.common import Unavailable,file_hash
from v13.memory_server import ROLE_SUFFIX
from v13.runners import LlamaRunner


class SparseRunnerLifecycle(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name)
        for d in ('bin','logs','config'):(self.home/d).mkdir()
        self.model=self.home/'model.gguf';self.model.write_bytes(b'software-model-fixture')
        script='#!'+sys.executable+'''\nimport sys
from http.server import BaseHTTPRequestHandler,HTTPServer
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        self.send_response(200);self.end_headers();self.wfile.write(b'{"status":"ok"}')
HTTPServer(('127.0.0.1',int(sys.argv[sys.argv.index('--port')+1])),Handler).serve_forever()
'''
        self.normal=self.home/'bin/llama-server';self.binary=self.home/'bin/llama-server-mem'
        for p in (self.normal,self.binary):p.write_text(script);p.chmod(0o755)
        self.native=self.home/'memory.bin';self.native.write_bytes(b'software-native-fixture')
        self.side=Path(str(self.native)+'.items.json')
        self.cur={'path':str(self.native),'sha256':file_hash(self.native),'base_model_sha256':file_hash(self.model),'batch_id':'fixture'}
        self.bind()
        (self.home/'config/memory-server.json').write_text(json.dumps({'binary_sha256':file_hash(self.binary)}))
        self.environment=patch.dict(os.environ,{},clear=False);self.environment.start()
        os.environ.pop('V13_LLAMA_SERVER',None);os.environ.pop('V13_MEMORY_FILE',None)
        self.runner=LlamaRunner(self.home,'C3_LANGUAGE',self.model,{'context_tokens':256,'threads':1})
        self.cancel=threading.Event()
    def bind(self,sidecar=True):
        if sidecar:
            self.side.write_text(json.dumps({'schema':'V13_SPARSE_DELIVERY_BINDINGS_V1','native_sha256':self.cur['sha256'],'rows':['m1'],'item_bindings':{}}))
            self.cur['sidecar_sha256']=file_hash(self.side)
        else:self.cur.pop('sidecar_sha256',None);self.side.unlink(missing_ok=True)
        (self.home/'config/lora-active.json').write_text(json.dumps({'C3_LANGUAGE'+ROLE_SUFFIX:self.cur}))
    def load(self):self.runner.load(self.cancel,time.monotonic()+4)
    def tearDown(self):
        self.runner.unload();self.environment.stop();self.tmp.cleanup()
    def test_capture_follows_health_and_warm_reuse_never_rehashes(self):
        from v13.memory_server import captured_delivery_binding
        healthy=[];original=self.runner._json
        def request(*a,**kw):
            answer=original(*a,**kw)
            if a[1]=='/health':healthy.append(answer['status'])
            return answer
        def capture(*a):
            self.assertEqual(healthy[-1],'ok');self.assertIsNone(self.runner._memory_delivery_binding)
            return captured_delivery_binding(*a)
        real_popen=subprocess.Popen
        with patch('v13.runners.subprocess.Popen',wraps=real_popen) as popen,patch.object(self.runner,'_json',side_effect=request),patch('v13.memory_server.captured_delivery_binding',side_effect=capture):
            self.load();binding=self.runner.memory_delivery_binding;pid=self.runner.proc.pid
            self.assertEqual(binding['path'],str(self.native));self.assertEqual(binding['sidecar_sha256'],file_hash(self.side))
            with patch('v13.memory_server.file_hash',side_effect=AssertionError('warm load must not reread model/native hashes')):
                self.load();self.assertEqual(self.runner.memory_delivery_binding,binding)
            self.assertEqual(self.runner.proc.pid,pid);self.assertEqual(popen.call_count,1)
            self.assertEqual(popen.call_args.args[0][0],str(self.binary))
            self.assertEqual(popen.call_args.kwargs['env']['V13_MEMORY_FILE'],str(self.native))
        binding['path']='external-mutation';self.assertEqual(self.runner.memory_delivery_binding['path'],str(self.native))
        self.runner.unload();self.assertIsNone(self.runner.memory_delivery_binding);self.assertIsNone(self.runner.memory)
    def test_legacy_native_without_map_still_runs_but_cannot_claim_binding(self):
        self.bind(sidecar=False);self.load()
        self.assertEqual(self.runner.memory['env']['V13_MEMORY_FILE'],str(self.native))
        self.assertIsNone(self.runner.memory_delivery_binding)

    def test_shared_library_change_invalidates_warm_child_even_with_same_launcher(self):
        from v13.memory_server import runtime_library_hashes
        lib=self.binary.parent/'libllama-server-impl.so';lib.write_bytes(b'synthetic shared runtime')
        (self.home/'config/memory-server.json').write_text(json.dumps({'binary_sha256':file_hash(self.binary),
            'runtime_libraries_sha256':runtime_library_hashes(self.binary)}))
        self.load();old=self.runner.proc
        self.assertIsNotNone(self.runner.memory_delivery_binding)
        binding=self.runner.memory_delivery_binding
        binding['runtime_libraries_sha256'].clear()
        self.assertIn(lib.name,self.runner.memory_delivery_binding['runtime_libraries_sha256'])
        lib.write_bytes(b'changed shared runtime')
        self.assertIsNone(self.runner.memory_delivery_binding)
        self.load()
        self.assertIsNotNone(old.poll());self.assertIsNone(self.runner.memory)
    def test_registry_deactivation_reaps_old_child_before_normal_load(self):
        self.load();old=self.runner.proc
        (self.home/'config/lora-active.json').write_text('{}')
        self.assertIsNone(self.runner.memory_delivery_binding)
        real_popen=subprocess.Popen
        with patch('v13.runners.subprocess.Popen',wraps=real_popen) as popen:self.load()
        self.assertIsNotNone(old.poll());self.assertIsNone(self.runner.memory);self.assertIsNone(self.runner.memory_delivery_binding)
        self.assertEqual(popen.call_args.args[0][0],str(self.normal));self.assertNotIn('V13_MEMORY_FILE',popen.call_args.kwargs['env'])
    def test_unapproved_inherited_memory_environment_never_enters_normal_child(self):
        (self.home/'config/lora-active.json').write_text('{}')
        real_popen=subprocess.Popen
        with patch.dict(os.environ,{'V13_MEMORY_FILE':'unapproved-shell-memory.bin'}),patch('v13.runners.subprocess.Popen',wraps=real_popen) as popen:
            self.load()
        self.assertNotIn('V13_MEMORY_FILE',popen.call_args.kwargs['env'])
        self.assertIsNone(self.runner.memory_delivery_binding)
    def test_native_forget_rewrite_and_reapproval_reload_instead_of_stale_reuse(self):
        self.load();old=self.runner.proc;before=self.runner.memory_delivery_binding
        self.native.write_bytes(b'zeroed-software-native-fixture');self.cur['sha256']=file_hash(self.native);self.bind()
        self.assertIsNone(self.runner.memory_delivery_binding);self.load()
        self.assertIsNotNone(old.poll());self.assertNotEqual(self.runner.proc.pid,old.pid)
        self.assertNotEqual(self.runner.memory_delivery_binding['native_sha256'],before['native_sha256'])
    def test_watched_model_binary_manifest_and_map_changes_force_revalidation(self):
        mutations=(self.model,self.binary,self.home/'config/memory-server.json',self.side)
        for changed in mutations:
            with self.subTest(path=changed.name):
                self.load();old=self.runner.proc;original=changed.read_bytes()
                changed.write_bytes(b'{}' if changed.name=='memory-server.json' else original+b' ')
                self.assertIsNone(self.runner.memory_delivery_binding);self.load()
                self.assertIsNotNone(old.poll());self.assertNotEqual(old.pid,self.runner.proc.pid)
                # A map change keeps the legacy native runner but removes the
                # evidence binding; all other changed hashes select normal.
                self.assertIsNone(self.runner.memory_delivery_binding)
                if changed!=self.side:self.assertIsNone(self.runner.memory)
                self.runner.unload();changed.write_bytes(original)
    def test_dead_child_and_failed_load_clear_binding_and_log(self):
        self.load();old=self.runner.proc;old.terminate();old.wait(timeout=2)
        self.assertIsNone(self.runner.memory_delivery_binding);self.load()
        self.assertNotEqual(old.pid,self.runner.proc.pid);self.assertIsNotNone(self.runner.memory_delivery_binding)
        self.runner.unload()
        with patch('v13.runners.subprocess.Popen',side_effect=OSError('software child start failure')):
            with self.assertRaises(OSError):self.load()
        self.assertIsNone(self.runner.proc);self.assertIsNone(self.runner.memory_delivery_binding);self.assertIsNone(self.runner.log_handle)
    def test_native_changed_during_health_handshake_never_publishes_binding(self):
        original=self.runner._json
        def health(*a,**kw):
            result=original(*a,**kw)
            if a[1]=='/health' and result.get('status')=='ok':self.native.write_bytes(b'rewritten-during-handshake')
            return result
        with patch.object(self.runner,'_json',side_effect=health):
            with self.assertRaises(Unavailable):self.load()
        self.assertIsNone(self.runner.proc);self.assertIsNone(self.runner.memory_delivery_binding);self.assertIsNone(self.runner.log_handle)


if __name__=='__main__':unittest.main()
