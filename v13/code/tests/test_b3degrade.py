"""WP-N19: B3-H10 automatic degradation (ten triggers, ladder L4..NO_MESSAGE) and the B3-H11 :doctor fields."""
import json
from pathlib import Path
import tempfile
import time
import unittest
import numpy as np
from v13 import b3calibration as B
from v13 import b3degrade as D
from v13 import callosum as C
from v13.contracts import packet
from v13.operator import Operator
from v13.runtime import Runtime
from v13.verification import b3_doctor

def ev(**kw):
    base={'receiver_revision':None,'runner_revision':None,'calibrated':False,'calibrated_at':None,'now':1e9,'message_rank':None,
          'message_effective_rank':None,'message_dim_std_min':None,'router_kl':None,'expert_flip':None,'retention_drop':None,
          'latent_utility':None,'channel_utility':{},'latency_ms':None,'resource_mode':None,'role_diversity':{'pairs':0,'jaccard':None}}
    return base|kw

class Ladder(unittest.TestCase):
    def test_canon_path_hard_and_soft(self):
        self.assertEqual(D.LADDER,('L4','L3','L2','L1','EXACT_SYMBOLIC','NO_MESSAGE'));self.assertEqual(len(D.TRIGGERS),10)
        self.assertEqual(D.decide('L3',['ROUTER_DRIFT']),'L2');self.assertEqual(D.decide('L1',['COST_OVER_BUDGET']),'EXACT_SYMBOLIC')
        self.assertEqual(D.decide('L4',['RUNNER_REVISION_CHANGED']),'EXACT_SYMBOLIC')  # hard: the bridge itself is invalid
        self.assertEqual(D.decide('L2',[]),'L2');self.assertEqual(D.decide('EXACT_SYMBOLIC',['ROUTER_DRIFT']),'EXACT_SYMBOLIC')
        self.assertEqual(D.decide('EXACT_SYMBOLIC',['MESSAGE_UTILITY_FELL']),'NO_MESSAGE');self.assertEqual(D.step_down('NO_MESSAGE'),'NO_MESSAGE')

    def test_every_trigger_reads_evidence_and_unmeasured_never_fires(self):
        st=D.empty()['dirs']['B1_TO_B2']
        none=D.triggers(st,ev(),'L2')
        self.assertTrue(none['CALIBRATION_EXPIRED'])  # a latent rung without calibration
        self.assertEqual([t for t,v in none.items() if v is not None],['CALIBRATION_EXPIRED'])
        st=dict(st,receiver_revision='r1',runner_revision='x1',baseline={'router_kl':.01,'expert_flip':.05,'retention_drop':.01})
        cases={'RECEIVER_REVISION_CHANGED':dict(receiver_revision='r2'),'RUNNER_REVISION_CHANGED':dict(runner_revision='x2'),
               'CALIBRATION_EXPIRED':dict(calibrated=True,calibrated_at=1e9-D.CAL_TTL_S-1),
               'PROJECTOR_COLLAPSED':dict(message_rank=16,message_effective_rank=2.),'ROUTER_DRIFT':dict(router_kl=.05),
               'EXPERT_FLIP_SPIKE':dict(expert_flip=.2),'RETENTION_REGRESSED':dict(retention_drop=.08),
               'MESSAGE_UTILITY_FELL':dict(latent_utility=.2,channel_utility={'SOURCE_EXACT':.5,'NO_MESSAGE':.1}),
               'COST_OVER_BUDGET':dict(resource_mode='ORANGE'),'ROLE_DIVERSITY_COLLAPSED':dict(role_diversity={'pairs':6,'jaccard':.9})}
        ok=dict(receiver_revision='r1',runner_revision='x1',calibrated=True,calibrated_at=1e9-60)
        for t,kw in cases.items():
            tr=D.triggers(st,ev(**(ok|kw)),'L2');self.assertTrue(tr[t],t)
            self.assertEqual([x for x,v in tr.items() if v],[t],t)
        calm=D.triggers(st,ev(**ok,router_kl=.015,expert_flip=.06,latency_ms=100.,resource_mode='YELLOW'),'L2')
        self.assertFalse(any(calm.values()))
        self.assertFalse(D.triggers(D.empty()['dirs']['B1_TO_B2'],ev(router_kl=9.),'L2')['ROUTER_DRIFT'])  # no baseline: no drift claim

class Live(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.r.sleep.cycle.set_policy('enabled','off')
        self.revs={'C3_LANGUAGE':'c3','B1_DETAIL':'rev-b1','B2_GIST':'rev-b2'};self.r.revisions=lambda:dict(self.revs)
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def bridge(self,d='B1_TO_B2',age=60.,gates=('l1',),receiver='rev-b2'):
        (self.r.home/'b3').mkdir(exist_ok=True)
        rng=np.random.default_rng(0);x=rng.normal(size=(80,8))
        cal=B.compute(x,x[::-1]*1.05,body_pair_id='B1->B2',sender_revision='rev-b1',receiver_revision=receiver,target_tap_id='lfm2.l8')|{'created_wall_time':time.time()-age}
        man={'calibrated':True,'created_wall_time':time.time()-age,'receiver_revision':receiver,'r':16,'K':4,'receiver_calibration':cal}
        man|={g+'_gate':{'verdict':'PASS','criteria':{'receiver_ood':{'significant':True}}} for g in gates}
        (self.r.home/'b3'/f'{d}.json').write_text(json.dumps(man))
    def doc(self):return b3_doctor(self.r)['B1_TO_B2']

    def test_fresh_runtime_reports_h11_fields_and_stays_off_latent(self):
        doc=self.doc()
        self.assertEqual((doc['latent_level'],doc['degradation_level'],doc['status']),('unavailable','EXACT_SYMBOLIC','PASS'))
        for k in ('router_kl','expert_flip'):self.assertEqual(set(doc[k]),{'baseline','current'})
        for k in ('body_revisions','runner_revision','calibration_valid','receiver_tap_ids','message_rank','slot_budget','latent_gain','utility_vs_no_message',
                  'fallback_channel','last_calibration','experience_count','hardware_proof_id'):self.assertIn(k,doc)
        self.assertEqual(set(doc['degradation']['triggers']),set(D.TRIGGERS));self.assertFalse(D.allowed(self.r.store,'B1_TO_B2','L1'))
        self.assertEqual(doc['body_revisions']['B2_GIST'],'rev-b2')

    def test_promotion_needs_human_and_evidence_then_resource_mode_demotes(self):
        with self.assertRaises(PermissionError):D.promote(self.r,'B1_TO_B2')
        with self.assertRaisesRegex(ValueError,'CALIBRATION'):D.promote(self.r,'B1_TO_B2','EXPLICIT_HUMAN')
        self.bridge(gates=());
        with self.assertRaisesRegex(ValueError,'GATE_L1'):D.promote(self.r,'B1_TO_B2','EXPLICIT_HUMAN')
        self.bridge();self.assertEqual(json.loads(Operator(self.r).run(':callosum promote B1_TO_B2'))['level'],'L1')
        self.assertTrue(D.allowed(self.r.store,'B1_TO_B2','L1'));self.assertFalse(D.allowed(self.r.store,'B1_TO_B2','L2'))
        self.assertEqual(self.doc()['degradation_level'],'L1')  # latent_level is then the bridge gate status (b3bridge.doctor_fields)
        self.r.guard.state='PRESSURE'  # §97.2 ORANGE: one body resident, latent exchange impossible
        doc=self.doc();self.assertEqual(doc['degradation_level'],'EXACT_SYMBOLIC');self.assertEqual(doc['degradation']['fired'],['COST_OVER_BUDGET'])
        row=self.r.store.one("SELECT metrics FROM telemetry WHERE kind='b3_degraded' ORDER BY id DESC LIMIT 1")
        self.assertEqual(json.loads(row['metrics']),{'direction':'B1_TO_B2','level_from':'L1','level_to':'EXACT_SYMBOLIC','triggers':['COST_OVER_BUDGET']})

    def test_soft_trigger_takes_one_rung_and_baseline_comes_from_promotion(self):
        self.bridge(gates=('l1','l2'));D.record(self.r.store,'B1_TO_B2',router_kl=.01)
        for _ in range(2):D.promote(self.r,'B1_TO_B2','EXPLICIT_HUMAN')
        self.assertEqual(D.level(self.r.store,'B1_TO_B2'),'L2');self.assertEqual(self.doc()['router_kl'],{'baseline':.01,'current':.01})
        D.record(self.r.store,'B1_TO_B2',router_kl=.05);doc=self.doc()
        self.assertEqual((doc['degradation']['previous'],doc['degradation_level'],doc['degradation']['fired']),('L2','L1',['ROUTER_DRIFT']))
        with self.assertRaises(ValueError):D.record(self.r.store,'B1_TO_B2',router_temperature=1.)

    def test_expired_calibration_is_a_doctor_fail_and_falls_back(self):
        self.bridge();D.promote(self.r,'B1_TO_B2','EXPLICIT_HUMAN');self.bridge(age=D.CAL_TTL_S+60)
        doc=self.doc();self.assertEqual((doc['status'],doc['degradation_level'],doc['calibration_valid']),('FAIL','EXACT_SYMBOLIC',False))
        again=self.doc();self.assertEqual(again['status'],'PASS');self.assertEqual(again['degradation']['last_fail']['reason'],'LATENT_ACTIVE_WITHOUT_VALID_CALIBRATION')

    def test_receiver_revision_change_on_the_message_path_demotes_at_once(self):
        self.bridge();D.promote(self.r,'B1_TO_B2','EXPLICIT_HUMAN')
        c=C.controller(self.r);c.choose('B1_DETAIL','B2_GIST','SOURCE_EXACT','rev-b2');self.assertEqual(D.level(self.r.store,'B1_TO_B2'),'L1')
        c.choose('B1_DETAIL','B2_GIST','SOURCE_EXACT','rev-b2-new');self.assertEqual(D.level(self.r.store,'B1_TO_B2'),'EXACT_SYMBOLIC')
        self.assertEqual(D.load(self.r.store)[0]['dirs']['B1_TO_B2']['log'][-1]['triggers'],['RECEIVER_REVISION_CHANGED'])

    def test_utility_moves_between_exact_symbolic_and_no_message(self):
        c=C.controller(self.r)
        def teach(ch,u):
            def fn(st):
                for _ in range(C.MIN_N):c._update(st,'B1_TO_B2',ch,u)
            c._mutate(fn)
        teach('NO_MESSAGE',.6);teach('SOURCE_EXACT',.2);teach('SYMBOLIC',.1)
        doc=self.doc();self.assertEqual((doc['degradation_level'],doc['fallback_channel']),('NO_MESSAGE','NO_MESSAGE'))
        teach('CONTROL',1.5);self.assertEqual(self.doc()['degradation_level'],'EXACT_SYMBOLIC')

    def test_role_diversity_from_real_offers(self):
        for i,(a,b) in enumerate([('Total is 391 euro','Total is 391 euro')]*6):
            e=self.r.store.event(self.r.session,'q%d'%i)
            for role,s in (('B1_DETAIL',a),('B2_GIST',b)):
                self.r.store.add_packet('OfferPacket',packet('OfferPacket',role,e['event_id'],e['brain_generation_id'],[],role=role,based_on_state_version=0,
                    deadline_monotonic_ns=time.monotonic_ns()+10**9,evidence_refs=[],offer={'summary':s,'quotes':[],'uncertainty':'','needs_reentry':False},confidence=0.,native_metrics={}))
        self.assertEqual(D.role_diversity(self.r.store),{'pairs':6,'jaccard':1.})
        self.bridge()
        with self.assertRaisesRegex(ValueError,'ROLE_DIVERSITY_COLLAPSED'):D.promote(self.r,'B1_TO_B2','EXPLICIT_HUMAN')  # no promotion into a collapsed pair

if __name__=='__main__':unittest.main()
