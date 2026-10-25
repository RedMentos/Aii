"""Run169 synthetic fake-native test for serialized private receiver and rollback."""
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.body_fp32_master_export_run162 import export
from scripts.body_fp32_master_micro_run166 import micro
from scripts.body_fp32_native_receiver_run169 import probe,PROMPTS_SHA,prompt_hash,GATES


def u32(x):return struct.pack('<I',x)
def u64(x):return struct.pack('<Q',x)
def s(x):
    b=x.encode();return u64(len(b))+b

class FakeRunner:
    live=0;max_live=0;unloads=0;fail_patched=False
    def __init__(self,home,role,model,cfg):
        if self.live:raise AssertionError('concurrent_native_runner')
        self.__class__.live+=1;self.__class__.max_live=max(self.max_live,self.live)
        self.model=Path(model)
    def generate(self,messages,cancel,deadline,max_tokens,seed):
        if self.fail_patched and self.model.name=='patched.gguf':
            raise RuntimeError('synthetic_native_failure')
        yield f'fake:{seed}:{messages[-1]["content"]}'
    def unload(self):
        self.__class__.live-=1;self.__class__.unloads+=1

class ReceiverTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.root=Path(t.name);self.model=self.root/'model.gguf';self.patched=self.root/'patched.gguf'
        self.master=self.root/'master.npz';self.report=self.root/'report.json'
        self.micro=self.root/'micro.npz';self.micro_report=self.root/'micro-report.json'
        h=b'GGUF'+u32(3)+u64(1)+u64(0)+s('norm.weight')+u32(1)+u64(4)+u32(0)+u64(0)
        h+=b'\0'*(-len(h)%32)
        self.model.write_bytes(h+np.array([1.,2.,3.,4.],dtype='<f4').tobytes())
        self.sha=hashlib.sha256(self.model.read_bytes()).hexdigest()
        r=export(self.model,self.sha,['norm.weight'],self.master);self.report.write_text(json.dumps(r))
        m=micro(self.model,self.master,self.report,self.sha,self.micro);self.micro_report.write_text(json.dumps(m))
        FakeRunner.live=0;FakeRunner.max_live=0;FakeRunner.unloads=0;FakeRunner.fail_patched=False

    def run_probe(self):
        return probe(self.model,self.master,self.report,self.micro,self.micro_report,
                     self.sha,self.patched,self.root,{},FakeRunner)

    def test_preregistered_prompt_hash(self):
        self.assertEqual(prompt_hash(),PROMPTS_SHA)

    def test_serial_receiver_and_private_rollback(self):
        r=self.run_probe()
        self.assertEqual(len(r['rows']),6)
        self.assertEqual(FakeRunner.max_live,1)
        self.assertEqual(FakeRunner.unloads,2)
        self.assertEqual(FakeRunner.live,0)
        self.assertEqual(self.patched.read_bytes(),self.model.read_bytes())
        self.assertEqual(r['body_training_authority'],0)
        self.assertEqual(r['gates'],GATES)
        self.assertTrue(all(x['same_output_hash'] for x in r['pairs']))

    def test_native_error_still_restores_and_unloads(self):
        FakeRunner.fail_patched=True
        with self.assertRaisesRegex(RuntimeError,'synthetic_native_failure'):
            self.run_probe()
        self.assertEqual(FakeRunner.live,0)
        self.assertEqual(FakeRunner.unloads,2)
        self.assertEqual(self.patched.read_bytes(),self.model.read_bytes())

    def test_wrong_registered_sha_rejected_without_output(self):
        with self.assertRaisesRegex(ValueError,'external_model_sha_mismatch'):
            probe(self.model,self.master,self.report,self.micro,self.micro_report,
                  '0'*64,self.patched,self.root,{},FakeRunner)
        self.assertFalse(self.patched.exists())

if __name__=='__main__':unittest.main()
