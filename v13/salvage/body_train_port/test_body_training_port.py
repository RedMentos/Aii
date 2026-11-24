import json,os,tempfile,unittest
from pathlib import Path
from v13.body_training import inspect_train_port
from v13.common import file_hash

class BodyTrainingPortContract(unittest.TestCase):
    def make(self,home):
        (home/'config').mkdir();(home/'models').mkdir();(home/'bin').mkdir()
        files={'model':'models/body.gguf','master':'models/body-master.bin','runner':'bin/train-body','requantizer':'bin/requantize-body'}
        for k,p in files.items():
            q=home/p;q.write_bytes((k+'-distinct').encode())
            if k in {'runner','requantizer'}:q.chmod(0o755)
        d={'schema':'v13-native-body-train-port-v1','role':'B1_DETAIL','master_dtype':'float16','trainable_parameter_ids':['layer.1.expert.2.w1'],**{k+'_artifact':p for k,p in files.items()},**{k+'_sha256':file_hash(home/p) for k,p in files.items()}}
        (home/'config/native-body-train-port.json').write_text(json.dumps(d));return d
    def test_absent_port_has_zero_authority(self):
        with tempfile.TemporaryDirectory() as td:
            x=inspect_train_port(td,'B1_DETAIL');self.assertFalse(x['available']);self.assertEqual(x['update_authority'],0)
    def test_bound_artifacts_still_do_not_grant_training_authority(self):
        with tempfile.TemporaryDirectory() as td:
            home=Path(td);self.make(home);x=inspect_train_port(home,'B1_DETAIL')
            self.assertTrue(x['port_bound']);self.assertEqual(x['reason'],'PORT_BOUND_PROOF_REQUIRED');self.assertEqual(x['update_authority'],0)
    def test_quantized_inference_file_cannot_be_master(self):
        with tempfile.TemporaryDirectory() as td:
            home=Path(td);d=self.make(home);d['master_artifact']=d['model_artifact'];d['master_sha256']=d['model_sha256']
            (home/'config/native-body-train-port.json').write_text(json.dumps(d));self.assertEqual(inspect_train_port(home,'B1_DETAIL')['reason'],'INFERENCE_ARTIFACT_IS_NOT_TRAIN_MASTER')
    def test_tamper_and_nontrainable_dtype_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            home=Path(td);d=self.make(home);(home/d['master_artifact']).write_bytes(b'tamper')
            self.assertEqual(inspect_train_port(home,'B1_DETAIL')['reason'],'HASH_MISMATCH_MASTER')
            home=home/'second';home.mkdir();d=self.make(home);d['master_dtype']='q4_0';(home/'config/native-body-train-port.json').write_text(json.dumps(d))
            self.assertEqual(inspect_train_port(home,'B1_DETAIL')['reason'],'MASTER_DTYPE_NOT_TRAINABLE')

class CapabilityIntegration(unittest.TestCase):
    def test_capability_profile_cannot_promote_bound_descriptor(self):
        from types import SimpleNamespace
        from v13.verification import native_capability_profile
        with tempfile.TemporaryDirectory() as td:
            home=Path(td);BodyTrainingPortContract().make(home)
            profile=native_capability_profile(SimpleNamespace(home=home))
            self.assertEqual(profile['body_training']['status'],'UNAVAILABLE')
            self.assertEqual(profile['body_training']['authority'],'NONE')
            self.assertEqual(profile['body_training']['ports']['B1_DETAIL']['update_authority'],0)
