"""WP-N20: B3-H4 receiver calibration packet, B3-H5 hard receiver gate, B3-H9 latent utility + validation window."""
import json
from pathlib import Path
import tempfile
import time
import unittest
import numpy as np
from v13 import b3calibration as B
from v13 import b3degrade as D
from v13.runtime import Runtime

KW=dict(body_pair_id='B1->B2',sender_revision='s1',receiver_revision='r1',target_tap_id='lfm2.l8')
rng=np.random.default_rng(7)
NATIVE=rng.normal(size=(96,12))*np.linspace(3,.3,12)

class Packet(unittest.TestCase):
    def test_every_canon_field_and_measured_values(self):
        cal=B.compute(NATIVE,NATIVE[rng.permutation(96)],**KW)
        self.assertTrue(set(B.REQUIRED)<=set(cal));self.assertTrue(set(B.OPTIONAL)<=set(cal))
        self.assertAlmostEqual(cal['norm_ratio'],1.,places=6);self.assertLess(cal['geometry_error'],1e-6);self.assertEqual(cal['sample_count'],96)
        self.assertAlmostEqual(cal['variance_ratio'],1.,places=6);self.assertIsNone(cal['manifold_distance']);self.assertIsNone(cal['router_kl'])  # unmeasured stays None
        self.assertEqual(cal['valid_until_revision'],'r1');self.assertEqual(cal,B.compute(NATIVE,NATIVE[np.random.default_rng(7).permutation(96)],**KW)|{'calibration_dataset_id':cal['calibration_dataset_id']})
        self.assertEqual(B.validity(cal,'r1','s1'),(True,[]));self.assertEqual(B.compatible(cal),[])

    def test_wrong_direction_message_is_caught_by_geometry_not_by_norm(self):
        rot=NATIVE[:,::-1].copy()  # same norms, spread on the receiver's quiet axes
        cal=B.compute(NATIVE,rot,**KW);self.assertAlmostEqual(cal['norm_ratio'],1.,places=6)
        self.assertGreater(cal['geometry_error'],B.GEOMETRY_MAX);self.assertEqual(B.compatible(cal),['GEOMETRY'])
        loud=B.compute(NATIVE,NATIVE*5,**KW);self.assertIn('NORM_RATIO',B.compatible(loud));self.assertIn('VARIANCE_RATIO',B.compatible(loud))

    def test_stale_or_thin_calibration_is_invalid(self):
        cal=B.compute(NATIVE,NATIVE,**KW)
        self.assertIn('STALE_RECEIVER_REVISION',B.validity(cal,'r2')[1]);self.assertIn('STALE_SENDER_REVISION',B.validity(cal,'r1','s2')[1])
        self.assertIn('TOO_FEW_SAMPLES',B.validity(B.compute(NATIVE[:10],NATIVE[:10],**KW),'r1')[1])
        self.assertIn('MOE_ROUTER_NOT_MEASURED',B.validity(B.compute(NATIVE,NATIVE,receiver_kind='moe',**KW),'r1')[1])
        self.assertIn('FIELD_MISSING:geometry_error',B.validity({k:v for k,v in cal.items() if k!='geometry_error'},'r1')[1])
        with self.assertRaises(ValueError):B.compute(NATIVE,NATIVE[:,:5],**KW)
        with self.assertRaises(ValueError):B.compute(NATIVE,NATIVE,injection_level=5,**KW)

class HardGate(unittest.TestCase):
    def test_canon_order(self):
        cal=B.compute(NATIVE,NATIVE,**KW)
        self.assertEqual(B.gate(None,'r1')['reasons'][0],'CALIBRATION_MISSING')
        self.assertEqual(B.gate(cal,'r2',ood_ok=True)['reasons'][0],'RECEIVER_REVISION_CHANGED')
        off=B.gate(cal,'r1',ood_ok=False,fallback='SYMBOLIC');self.assertEqual((off['latent'],off['fallback'],off['reasons']),('OFF','SYMBOLIC',['OOD_GATE']))
        self.assertEqual(B.gate(cal,'r1')['reasons'],['OOD_NOT_MEASURED'])
        flat=B.gate(cal,'r1',ood_ok=True,latent_utility=.3,fallback_utility=.3)
        self.assertEqual((flat['latent'],flat['authority_may_increase'],flat['reasons']),('ON',False,['UTILITY_NOT_ABOVE_FALLBACK']))
        self.assertTrue(B.gate(cal,'r1',ood_ok=True,latent_utility=.4,fallback_utility=.3)['authority_may_increase'])

    def test_moe_receiver_needs_calibrated_router_thresholds(self):
        cal=B.compute(NATIVE,NATIVE,receiver_kind='moe',router_kl=.02,expert_flip_rate=.05,residual_norm_shift=.1,**KW)
        self.assertTrue(all(r.startswith('THRESHOLD_UNCALIBRATED') for r in B.gate(cal,'r1',ood_ok=True)['reasons']))
        t={'B3.max_router_kl':.01,'B3.max_expert_flip_rate':.1,'B3.max_residual_norm_shift':.2}
        self.assertEqual(B.gate(cal,'r1',ood_ok=True,thresholds=t)['reasons'],['ROUTER_GATE:router_kl'])
        self.assertEqual(B.gate(cal,'r1',ood_ok=True,thresholds=t|{'B3.max_router_kl':.05})['latent'],'ON')

class Utility(unittest.TestCase):
    def test_penalties_and_validation_window(self):
        u,parts=B.latent_utility(1.,.5,.25,.1,.05,router_drift=.2,retention_drop=-.1)
        self.assertAlmostEqual(u,1.4);self.assertEqual((parts['router_drift_penalty'],parts['retention_penalty']),(.2,0.))
        r=np.random.default_rng(1);base=list(r.normal(.3,.05,40));lat=[b+.1 for b in base]
        self.assertEqual(B.latent_preferred({'LATENT':lat[:10],'NO_MESSAGE':base[:10]})['reason'],'VALIDATION_WINDOW_TOO_SHORT')
        self.assertTrue(B.latent_preferred({'LATENT':lat,'NO_MESSAGE':base,'SOURCE_EXACT':base})['preferred'])
        ex=[b+.2 for b in base]
        res=B.latent_preferred({'LATENT':lat,'NO_MESSAGE':base,'SOURCE_EXACT':ex});self.assertEqual((res['preferred'],res['reason']),(False,'DOES_NOT_BEAT_ALL_BASELINES'))
        self.assertEqual(B.latent_preferred({'LATENT':lat,'SOURCE_EXACT':base})['reason'],'NO_MESSAGE_BASELINE_MISSING')

class Ladder(unittest.TestCase):
    def test_promotion_reads_the_packet_and_a_sender_swap_demotes(self):
        with tempfile.TemporaryDirectory() as t:
            r=Runtime(Path(t))
            try:
                revs={'B1_DETAIL':'s1','B2_GIST':'r1','C3_LANGUAGE':'c'};r.revisions=lambda:dict(revs);(r.home/'b3').mkdir()
                man={'receiver_revision':'r1','l1_gate':{'verdict':'PASS','criteria':{'receiver_ood':{'significant':True}}},
                     'receiver_calibration':B.compute(NATIVE,NATIVE[:,::-1].copy(),**KW)|{'created_wall_time':time.time()}}
                (r.home/'b3/B1_TO_B2.json').write_text(json.dumps(man))
                with self.assertRaisesRegex(ValueError,'B3_H5:COMPATIBILITY:GEOMETRY'):D.promote(r,'B1_TO_B2','EXPLICIT_HUMAN')
                man['receiver_calibration']=B.compute(NATIVE,NATIVE,**KW)|{'created_wall_time':time.time()};(r.home/'b3/B1_TO_B2.json').write_text(json.dumps(man))
                self.assertEqual(D.promote(r,'B1_TO_B2','EXPLICIT_HUMAN'),'L1')
                revs['B1_DETAIL']='s2'  # new sender body: the calibration no longer describes these messages
                out=D.check(r)['B1_TO_B2'];self.assertEqual((out['level'],out['status']),('EXACT_SYMBOLIC','FAIL'))
                self.assertIn('STALE_SENDER_REVISION',out['calibration_reasons'])
            finally:r.close()

if __name__=='__main__':unittest.main()
