"""Run177 synthetic readout-provenance regression, no native model launched."""
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from v13.runners import LlamaRunner,TAP_SPECS

class DummyProc:
    pid=os.getpid()
    def poll(self):return None

class TapIdentity(unittest.TestCase):
    def read(self,role,dim,expected,from_pool=False):
        with tempfile.TemporaryDirectory() as d:
            r=LlamaRunner(Path(d),role,Path(d)/'missing.gguf',{},purpose='tap')
            r.proc=DummyProc()
            r.load=lambda cancel,deadline:None
            if from_pool:
                spec=TAP_SPECS[{'B1_DETAIL':'body','B2_GIST':'gist','C3_LANGUAGE':'language'}[role]]
                r.tap_id,r.tap_dim=spec
            def response(method,path,payload,deadline,**kwargs):
                if path=='/tokenize':return {'tokens':[10,11,12]}
                if path=='/embeddings':return [{'embedding':[[.25]*dim for _ in range(3)]}]
                raise AssertionError(path)
            r._json=response
            packet=r.tap('synthetic readout',threading.Event(),time.monotonic()+10,max_tokens=64)
            self.assertEqual(packet['metrics']['tap_id'],expected)
            self.assertEqual(packet['metrics']['embedding_dim'],dim)
            self.assertEqual(packet['token_ids'],[10,11,12])
            self.assertFalse(packet['metrics']['CAN_TRAIN_BODY'])
            self.assertFalse(packet['metrics']['CAN_LATENT_INJECT'])
    def test_direct_b1_identity_unchanged(self):
        self.read('B1_DETAIL',2048,'lfm2.result_norm.final.v1')
    def test_direct_b2_identity_and_dimension(self):
        self.read('B2_GIST',1024,'qwen35.result_norm.final.v1')
    def test_pool_bound_b2_identity_and_dimension(self):
        self.read('B2_GIST',1024,'qwen35.result_norm.final.v1',from_pool=True)
    def test_c3_identity_unchanged(self):
        self.read('C3_LANGUAGE',1024,'lfm2.result_norm.final.v1')

if __name__=='__main__':unittest.main()
