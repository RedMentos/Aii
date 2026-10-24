from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import body_jepa_resume as R
import body_jepa_micro as B

class Resume(unittest.TestCase):
    def test_uninterrupted_equals_60_100_bitwise(self):
        full=R.Session().advance(160)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'ckpt';R.save(R.Session().advance(60),p)
            resumed=R.load(p).advance(100)
            self.assertTrue(R.bitwise_equal(full,resumed))
            self.assertEqual(full.heldout_mse(),resumed.heldout_mse())
            self.assertTrue(all(p.grad is None for p in resumed.model.target.parameters()))
    def test_wrong_target_negative_control_bitwise(self):
        full=R.Session(True).advance(160)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'ckpt';R.save(R.Session(True).advance(60),p)
            resumed=R.load(p).advance(100)
            self.assertTrue(R.bitwise_equal(full,resumed))
            self.assertEqual(full.heldout_mse(),resumed.heldout_mse())
    def test_hash_corruption_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'ckpt';R.save(R.Session().advance(60),p)
            f=p/'state.npz';b=bytearray(f.read_bytes());b[-2]^=1;f.write_bytes(b)
            with self.assertRaisesRegex(ValueError,'integrity'):R.load(p)
    def test_dataset_hash_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'ckpt';R.save(R.Session().advance(60),p)
            import json
            f=p/'MANIFEST.json';o=json.loads(f.read_text());o['dataset_sha256']='0'*64;f.write_text(json.dumps(o))
            with self.assertRaisesRegex(ValueError,'dataset'):R.load(p)
    def test_closed_manifest_rejects_unexpected_authority(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'ckpt';R.save(R.Session().advance(60),p)
            import json
            f=p/'MANIFEST.json';o=json.loads(f.read_text());o['native_body_gate_pass']=True
            f.write_text(json.dumps(o))
            with self.assertRaisesRegex(ValueError,'integrity'):R.load(p)
    def test_closed_manifest_rejects_extra_field(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'ckpt';R.save(R.Session().advance(60),p)
            import json
            f=p/'MANIFEST.json';o=json.loads(f.read_text());o['trusted']=True
            f.write_text(json.dumps(o))
            with self.assertRaisesRegex(ValueError,'integrity'):R.load(p)
    def test_no_overwrite_and_invalid_step(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'ckpt';s=R.Session().advance(60);R.save(s,p)
            with self.assertRaises(FileExistsError):R.save(s,p)
            with self.assertRaises(ValueError):s.advance(101)
    def test_source_revision_bound(self):
        self.assertTrue(R.source_ok())
        self.assertEqual(R.SOURCE_SHA256,'af899ca76c615e1b0954a4c3727601ff58c24ab496268289170d5360aa5daa11')
    def test_no_age_or_native_authority(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'ckpt';info=R.save(R.Session().advance(60),p)
            self.assertEqual(info['authority'],'SYNTHETIC_SANDBOX_NO_AGE_ACTION')
            self.assertFalse(info['native_body_gate_pass'])

if __name__=='__main__':unittest.main()
