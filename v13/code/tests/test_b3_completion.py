"""WP-U9 B3-H12: the LATENT completion gate reads evidence and only reports allowed intermediate statuses."""
import json
from pathlib import Path
import tempfile
import unittest
from v13 import b3bridge as BB

CRIT={k:{'significant':True} for k in ('beats_no_message','utility_beats_exact','utility_beats_control','utility_beats_symbolic','receiver_ood','restart_reproducibility')}

class Gate(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def man(self,verdict='PASS',**kw):
        (self.home/'b3').mkdir(exist_ok=True)
        (self.home/'b3/B1_TO_B2.json').write_text(json.dumps({'calibrated':True,'receiver_revision':'r1','l1_gate':{'verdict':verdict,'criteria':CRIT}}|kw))
    def test_without_bridge_is_scaffold_and_lists_missing(self):
        g=BB.completion_gate(self.home,'B1_TO_B2',{'fallback_channel':'SOURCE_EXACT','experience_count':0})
        self.assertEqual(g['status'],'scaffold');self.assertFalse(g['B3_LATENT_IMPLEMENTED']);self.assertEqual(g['latent_authority'],0)
        self.assertTrue(g['criteria']['CODE']);self.assertTrue(g['criteria']['INTEGRATION_TESTS'])
        self.assertIn('REAL_SENDER_STATE_PATH',g['missing']);self.assertIn('NO_MESSAGE_ABLATION',g['missing'])
    def test_l1_pass_gives_l1_shadow_but_not_implemented(self):
        self.man()
        g=BB.completion_gate(self.home,'B1_TO_B2',{'bridge':{'stale_receiver_revision':False},'fallback_channel':'SOURCE_EXACT','experience_count':3},messages=2)
        self.assertEqual(g['status'],'L1_shadow')
        for k in ('RECEIVER_CALIBRATED_BRIDGE','OOD_GATE','RESTART_PERSISTENCE','NO_MESSAGE_ABLATION','EXACT_ABLATION','SYMBOLIC_CONTROL_ABLATION','TELEMETRY','FALLBACK_CHANNELS'):
            self.assertTrue(g['criteria'][k],k)
        self.assertEqual(sorted(g['missing']),['REAL_RECEIVER_EFFECT','REAL_SENDER_STATE_PATH','REAL_TARGET_RUNNER_MEASUREMENT','ROUTER_STABILITY_METRICS'])
        stale=BB.completion_gate(self.home,'B1_TO_B2',{'bridge':{'stale_receiver_revision':True}})
        self.assertEqual(stale['status'],'scaffold')  # a stale receiver revision voids the L1 shadow status
    def test_only_all_criteria_make_it_active(self):
        self.man()
        row={'bridge':{},'fallback_channel':'SOURCE_EXACT','experience_count':3,'native_taps':True,'receiver_tap_ids':['t'],'latent_gain':.1,'router_kl':.01,'hardware_proof_id':'p'}
        g=BB.completion_gate(self.home,'B1_TO_B2',row,messages=1);self.assertEqual((g['status'],g['B3_LATENT_IMPLEMENTED']),('active',True))
        self.assertEqual(BB.completion_gate(self.home,'B1_TO_B2',row,messages=0)['status'],'L1_shadow')  # no telemetry

class Doctor(unittest.TestCase):
    def test_doctor_reports_completion_per_direction(self):
        from v13.runtime import Runtime
        from v13.verification import b3_doctor
        with tempfile.TemporaryDirectory() as t:
            r=Runtime(Path(t))
            try:
                out=b3_doctor(r)
                for d in ('B1_TO_B2','B2_TO_B1'):self.assertEqual(out[d]['completion']['status'],'scaffold');self.assertFalse(out[d]['completion']['B3_LATENT_IMPLEMENTED'])
            finally:r.close()

if __name__=='__main__':unittest.main()
