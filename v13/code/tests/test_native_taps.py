"""Shape/provenance failure paths; actual vectors are checked by integration_taps."""
from pathlib import Path
import tempfile
import time
import unittest
from v13.common import Unavailable,atomic_write,file_hash,dumps
from v13.runtime import Runtime
from v13.contracts import packet

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
        p=packet('LatentTapPacket','B1_DETAIL',e['event_id'],e['brain_generation_id'],[e['source_ref']],role='B1_DETAIL',source_ref=e['source_ref'],tap_id='unit_fixture_not_native',model_revision='fixture',token_ids=[1],feature_path='data/blobs/tap-fixture.json',feature_sha256=file_hash(path),shape=[1,2]);r.store.add_packet('LatentTapPacket',p)
        self.assertEqual(r.cognition.read_tap(p)['vectors'],[[.1,.2]])
        atomic_write(path,'tampered')
        with self.assertRaises(ValueError):r.cognition.read_tap(p)
        self.assertTrue(any('Tap-Artefakt' in x for x in r.store.integrity(True)))

if __name__=='__main__':unittest.main()
