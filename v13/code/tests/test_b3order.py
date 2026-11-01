"""WP-N22: B3-H8 training order from evidence; joint-movement guard; promotion and :doctor read it."""
import json
from pathlib import Path
import tempfile
import time
import unittest
import numpy as np
from v13 import b3calibration as B
from v13 import b3degrade as D
from v13 import b3order as O
from v13.runtime import Runtime
from v13.verification import b3_doctor

REVS={'B1_DETAIL':'s1','B2_GIST':'r1','C3_LANGUAGE':'c'}
X=np.random.default_rng(3).normal(size=(80,6))

def write(home,**man):
    (Path(home)/'b3').mkdir(exist_ok=True);(Path(home)/'b3/B1_TO_B2.json').write_text(json.dumps(man))

def full(**kw):
    cal=B.compute(X,X,body_pair_id='B1->B2',sender_revision='s1',receiver_revision='r1',target_tap_id='t')|{'created_wall_time':time.time()}
    return {'sender_revision':'s1','receiver_revision':'r1','sha256':'0'*64,'train':{'samples':80},'receiver_calibration':cal,
            'l1_gate':{'verdict':'PASS','criteria':{'receiver_ood':{'significant':True}}}}|kw

class Order(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def test_steps_in_canon_order_and_next_step(self):
        self.assertEqual(len(O.STEPS),10)
        st=O.status(self.home,'B1_TO_B2',REVS);self.assertEqual((st['done'],st['next'],st['status']),([],'FREEZE_B1','IN_ORDER'))
        write(self.home,**full());st=O.status(self.home,'B1_TO_B2',REVS)
        self.assertEqual(st['done'],list(O.STEPS[:6]));self.assertEqual(st['next'],'L2_SHADOW');self.assertIn('L3_SHADOW',st['locked_by_canon'])
        st=O.status(self.home,'B1_TO_B2',dict(REVS,B2_GIST='r2'))  # receiver body moved since training
        self.assertEqual((st['done'],st['next']),(['FREEZE_B1'],'FREEZE_B2'))
        self.assertEqual(st['violations'],['PAIRED','TRAIN_BRIDGE','L1_UTILITY']);self.assertEqual(st['status'],'ORDER_VIOLATION')
    def test_too_few_pairs_and_skips_are_refused(self):
        write(self.home,**full(train={'samples':10},l2_gate={'verdict':'PASS'}))
        st=O.status(self.home,'B1_TO_B2',REVS);self.assertEqual(st['next'],'PAIRED');self.assertIn('L2_SHADOW',st['violations'])
        with self.assertRaisesRegex(PermissionError,'erst nach PAIRED'):O.require(self.home,'B1_TO_B2',REVS,'L1_UTILITY')
        self.assertEqual(O.require(self.home,'B1_TO_B2',REVS,'FREEZE_B1')['next'],'PAIRED')
    def test_joint_movement_guard(self):
        write(self.home,**full());st=O.status(self.home,'B1_TO_B2',REVS)
        self.assertTrue(O.check_job(['sender_bridge','receiver_adapter'],st))
        with self.assertRaisesRegex(PermissionError,'gemeinsam'):O.check_job(['sender_bridge','receiver_backbone'],st)
        with self.assertRaisesRegex(PermissionError,'eingefroren'):O.check_job(['receiver_backbone'],st)
        with self.assertRaisesRegex(PermissionError,'getrennt'):O.check_job(['receiver_router','receiver_adapter'],st)
        with self.assertRaisesRegex(PermissionError,'Ko-Adaption'):O.check_job(['receiver_router'],st)
        with self.assertRaises(ValueError):O.check_job(['everything'],st)
        done=O.status(self.home,'B1_TO_B2',REVS)|{'next':'ROUTER_LEARNING'};self.assertTrue(O.check_job(['receiver_router'],done))

class Live(unittest.TestCase):
    def test_promotion_and_doctor_follow_the_order(self):
        with tempfile.TemporaryDirectory() as t:
            r=Runtime(Path(t))
            try:
                r.revisions=lambda:dict(REVS)
                write(r.home,**full(train={'samples':8}))
                with self.assertRaisesRegex(ValueError,'B3_H8:PAIRED'):D.promote(r,'B1_TO_B2','EXPLICIT_HUMAN')
                write(r.home,**full());self.assertEqual(D.promote(r,'B1_TO_B2','EXPLICIT_HUMAN'),'L1')
                with self.assertRaisesRegex(ValueError,'B3_H8:L2_SHADOW'):D.promote(r,'B1_TO_B2','EXPLICIT_HUMAN')
                doc=b3_doctor(r)['B1_TO_B2']['training_order'];self.assertEqual((doc['next'],doc['status']),('L2_SHADOW','IN_ORDER'))
            finally:r.close()

if __name__=='__main__':unittest.main()
