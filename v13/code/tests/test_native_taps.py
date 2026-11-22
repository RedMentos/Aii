"""Shape/provenance failure paths; actual vectors are checked by integration_taps."""
from pathlib import Path
import os
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from v13.common import Unavailable,atomic_write,file_hash,dumps
from v13.runtime import Runtime
from v13.contracts import packet
from v13.runners import LlamaRunner

class TapBinding(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name))
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def test_foreign_event_source_cannot_be_tapped(self):
        r=self.r;a=r.store.event(r.session,'one');b=r.store.event(r.session,'two')
        with self.assertRaises(ValueError):r.cognition.tap('B1_DETAIL',a,b['source_ref'],time.monotonic()+1)
        self.assertEqual(r.store.rows("SELECT * FROM packets WHERE kind='LatentTapPacket'"),[])
    def test_unsupported_role_or_missing_body_cannot_claim_tap(self):
        with self.assertRaises(Unavailable):self.r.pool.get_tap('C3_LANGUAGE')
        with self.assertRaises(Unavailable):self.r.pool.get_tap('B1_DETAIL')
    def test_tamper_or_dangling_source_detected_on_read_and_doctor(self):
        r=self.r;e=r.store.event(r.session,'Numerical binding fixture');path=r.home/'data/blobs/tap-fixture.json';atomic_write(path,dumps({'token_ids':[1],'vectors':[[.1,.2]]}))
        p=packet('LatentTapPacket','B1_DETAIL',e['event_id'],e['brain_generation_id'],[e['source_ref']],role='B1_DETAIL',source_ref=e['source_ref'],tap_id='unit_fixture_not_native',model_revision='fixture',sender_model_sha256='a'*64,tokenizer_revision=None,token_ids=[1],feature_path='data/blobs/tap-fixture.json',feature_sha256=file_hash(path),shape=[1,2]);r.store.add_packet('LatentTapPacket',p)
        self.assertEqual(r.cognition.read_tap(p)['vectors'],[[.1,.2]])
        atomic_write(path,'tampered')
        with self.assertRaises(ValueError):r.cognition.read_tap(p)
        self.assertTrue(any('Tap-Artefakt' in x for x in r.store.integrity(True)))

class NativeTapIdentity(unittest.TestCase):
    def _tap(self,role,expected_id,dimension,bound=None):
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder)
            runner=LlamaRunner(home,role,home/'unused.gguf',{},purpose='tap')
            runner.proc=SimpleNamespace(pid=os.getpid(),poll=lambda:None)
            runner.load=lambda cancel,deadline:None
            if bound is not None:
                runner.tap_id,runner.tap_dim=bound
            def request(method,path,payload,deadline,timeout_cap=3.):
                if path=='/tokenize':return {'tokens':[101,202]}
                if path=='/embeddings':
                    return [{'embedding':[[.25]*dimension,[.5]*dimension]}]
                raise AssertionError(path)
            runner._json=request
            with patch('v13.runners.process_memory',return_value={'rss_bytes':0}):
                result=runner.tap('synthetic source',threading.Event(),time.monotonic()+10)
            self.assertEqual(result['tap_id'],expected_id)
            self.assertEqual(result['metrics']['tap_id'],expected_id)
            self.assertEqual(result['metrics']['embedding_dim'],dimension)
            self.assertEqual(result['token_ids'],[101,202])
            self.assertFalse(result['metrics']['CAN_LATENT_INJECT'])
            self.assertFalse(result['metrics']['CAN_TRAIN_BODY'])

    def test_direct_b1_and_c3_keep_lfm2_tap_identity(self):
        self._tap('B1_DETAIL','lfm2.result_norm.final.v1',2048)
        self._tap('C3_LANGUAGE','lfm2.result_norm.final.v1',1024)

    def test_direct_b2_defaults_to_two_body_qwen_1024d(self):
        self._tap('B2_GIST','qwen35.result_norm.final.v1',1024)

    def test_pool_bound_b2_shared_body_uses_lfm2_2048d(self):
        from v13.runners import TAP_SPECS
        self._tap('B2_GIST','lfm2.result_norm.final.v1',2048,TAP_SPECS['body'])

    def test_cross_role_tap_binding_fails_before_native_request(self):
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder)
            runner=LlamaRunner(home,'B1_DETAIL',home/'unused.gguf',{},purpose='tap')
            runner.tap_id='qwen35.result_norm.final.v1'
            runner.tap_dim=1024
            with self.assertRaises(Unavailable):
                runner.tap('synthetic source',threading.Event(),time.monotonic()+10)


if __name__=='__main__':unittest.main()
