"""WP-N9: self model, interoception, corollary attribution (G-SELF-WORLD-005 cases), self-messaging gate, self-edit. No models."""
import json
import tempfile
import unittest
from pathlib import Path
from v13.runtime import Runtime
from v13.operator import Operator
from v13 import selfmodel as S
from v13 import neuromod as N

CFG={'minimum_free_mb':512,'thermal_limit_c':45,'deadline_seconds':60}
MB=1024*1024

def snap(avail_mb=8000,total_mb=12000,temp=30.,battery=80.,charging=False,own_mb=0):
    return {'mem_available_bytes':avail_mb*MB,'mem_total_bytes':total_mb*MB,'battery_temperature_c':temp,'battery_percent':battery,
            'charging':charging,'free_disk_bytes':50*1024**3,'processes':[{'rss_bytes':own_mb*MB}]}

class InteroceptionTests(unittest.TestCase):
    def test_calm_body(self):
        b=S.interoception(snap(),CFG)
        self.assertEqual(b['feeling'],'calm');self.assertEqual(b['signals']['ram_pressure'],0.);self.assertTrue(b['modulation']['dream_allowed'])
    def test_pressure_heat_and_low_battery_modulate(self):
        b=S.interoception(snap(avail_mb=600,temp=44,battery=10),CFG,[{'status':'ERROR','duration_s':50}])
        self.assertEqual(b['feeling'],'strained');self.assertFalse(b['modulation']['learning_allowed']);self.assertFalse(b['modulation']['dream_allowed'])
        self.assertLess(b['modulation']['context_budget_scale'],1.);self.assertLess(b['modulation']['compute_scale'],1.)
        self.assertEqual(S.interoception(snap(battery=10,charging=True),CFG)['signals']['energy_low'],0.)
    def test_self_caused_load_is_attenuated_in_salience_not_in_signal(self):
        own=S.interoception(snap(avail_mb=1000,total_mb=3000,own_mb=1800),CFG,own_active=True)
        ext=S.interoception(snap(avail_mb=1000,total_mb=3000,own_mb=1800),CFG,own_active=False)
        self.assertEqual(own['signals']['ram_pressure'],ext['signals']['ram_pressure'])
        self.assertLess(own['salience']['ram_pressure'],ext['salience']['ram_pressure']);self.assertTrue(own['safety_reads_raw'])
    def test_missing_sensors_stay_none(self):
        b=S.interoception({},CFG);self.assertIsNone(b['signals']['heat']);self.assertEqual(b['feeling'],'calm')

class AttributionTests(unittest.TestCase):
    """G-SELF-WORLD-005 (§85.7): the six required cases."""
    def cor(self,aid='a1',t0=100.,preds=None,affected=('ram',)):
        return {'action_id':aid,'issued_at':t0,'window_s':10.,'affected':list(affected),
                'predicted_observations':preds or [{'channel':'status','value':'FINAL'},{'channel':'duration_s','value':5.,'tolerance':1.}]}
    def test_same_external_event_without_self_action(self):
        self.assertEqual(S.attribute([],{'channel':'status','value':'FINAL','t':105})['class'],'EXTERNAL')
    def test_same_observation_following_self_action(self):
        a=S.attribute([self.cor()],{'channel':'status','value':'FINAL','t':105});self.assertEqual(a['class'],'SELF');self.assertEqual(a['action_ids'],['a1'])
    def test_partial_action_failure(self):
        a=S.attribute([self.cor()],{'channel':'status','value':'ERROR','t':105});self.assertEqual(a['class'],'MIXED')
        b=S.attribute([self.cor()],{'channel':'duration_s','value':9.,'t':105});self.assertEqual(b['class'],'MIXED');self.assertAlmostEqual(b['residual'],4.)
    def test_delayed_outcome(self):
        a=S.attribute([self.cor()],{'channel':'status','value':'FINAL','t':125});self.assertEqual(a['class'],'SELF');self.assertTrue(a['delayed'])
        self.assertEqual(S.attribute([self.cor()],{'channel':'status','value':'FINAL','t':200})['class'],'EXTERNAL')  # beyond 3x window
    def test_unexpected_side_effect(self):
        a=S.attribute([self.cor()],{'channel':'ram','value':1,'t':103});self.assertEqual((a['class'],a['reason']),('UNCLEAR','unexpected_side_effect'))
        self.assertEqual(S.attribute([self.cor()],{'channel':'battery','value':1,'t':103})['class'],'EXTERNAL')
    def test_ambiguous_causality(self):
        a=S.attribute([self.cor('a1'),self.cor('a2',101.)],{'channel':'status','value':'FINAL','t':105})
        self.assertEqual((a['class'],a['action_ids']),('UNCLEAR',['a1','a2']))
    def test_nearest_prediction_and_far_values_abstain(self):
        # thread L 2026-10-12 (bench-results/corollary-unclear-20261012): residual against the nearest open prediction;
        # far outside every own prediction -> UNCLEAR (no own error learned, no foreign claim)
        a1=self.cor('a1',100.,[{'channel':'n','value':10.,'tolerance':2.}]);a2=self.cor('a2',101.,[{'channel':'n','value':50.,'tolerance':2.}])
        m=S.attribute([a1,a2],{'channel':'n','value':56.,'t':105});self.assertEqual((m['class'],m['action_ids'],m['residual']),('MIXED',['a2'],6.))
        far=S.attribute([a1],{'channel':'n','value':700.,'t':105});self.assertEqual((far['class'],far['reason'],far['action_ids']),('UNCLEAR','far_outside_own_prediction',[]))
        self.assertEqual(S.attribute([a1],{'channel':'n','value':10.+S.FAR_K*2.,'t':105})['class'],'MIXED')  # boundary still own
    def test_missing_corollary_degrades_monitoring_measurably(self):
        obs=[{'channel':'status','value':'FINAL','t':105},{'channel':'duration_s','value':5.2,'t':105}]
        with_copy=[S.attribute([self.cor()],o)['class'] for o in obs];without=[S.attribute([],o)['class'] for o in obs]
        self.assertEqual(with_copy.count('SELF'),2);self.assertEqual(without.count('SELF'),0)  # own outcomes misread as external

class Base(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.r.sleep.cycle.set_policy('enabled','off')
        self.n=N.Neuromod(self.r.store);self.t=[1000.];self.s=S.SelfSystem(self.r,None,self.n,clock=lambda:self.t[0])
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def ev(self,text='x'):return self.r.store.event(self.r.session,text)['event_id']

class SystemTests(Base):
    def test_issue_observe_writes_packets_and_world_error_modulator(self):
        e=self.ev();p=self.s.issue(e,'act1','reply',[{'channel':'duration_s','value':2.,'tolerance':.5}],refs=[])
        self.assertEqual(p['permission_snapshot']['permission'],'local_text_only')
        self.t[0]=1001.;out=self.s.observe(e,[{'channel':'duration_s','value':6.,'t':1001.}],close=['act1'])
        self.assertEqual(out[0]['class'],'MIXED');self.assertEqual(self.s.report()['open_corollaries'],0)
        mods=[json.loads(r['payload']) for r in self.r.store.rows("SELECT payload FROM packets WHERE kind='ModulatorPacket' AND event_id=?",(e,))]
        self.assertTrue(any(m.get('path_id')=='world_predictor' and m['channels']['world_prediction_error']>0 for m in mods))
        self.assertEqual(self.s.corollary_view()['recent_own_action_outcomes'][0]['attribution'],'MIXED')
    def test_self_messages_are_gated_held_at_age0_deduped(self):
        self.assertEqual(self.s.message('error','low relevance',.3)['status'],'BELOW_RELEVANCE')
        self.assertEqual(self.s.message('error','disk almost full',.9)['status'],'HELD')
        self.assertEqual(self.s.message('error','disk almost full',.9)['status'],'SUPPRESSED_DUPLICATE')
        with self.assertRaises(ValueError):self.s.message('chat','hi',.9)
    def test_self_message_rate_limit_when_allowed(self):
        self.s._allowed=lambda right:True;got=[]
        for i in range(5):self.t[0]+=700;got.append(self.s.message('finding','found %d'%i,.9)['status'])
        self.assertEqual(got[:3],['DELIVERED']*3);self.assertEqual(got[3],'RATE_LIMITED')
        self.t[0]+=1;self.assertEqual(self.s.message('finding','another',.9)['status'],'RATE_LIMITED')
    def test_late_disagreeing_offer_becomes_held_finding(self):
        offer={'role':'B1_DETAIL','offer':{'summary':'The total is 42.5 not 40','needs_reentry':False},'evidence_refs':[]}
        self.assertEqual(self.s.late_offer('e',offer,'The total is 42.5, not 40.'),None)
        m=self.s.late_offer('e',offer,'The total is 40.');self.assertEqual((m['kind'],m['status']),('finding','HELD'))
    def test_self_edit_needs_human_and_rolls_back(self):
        from v13 import context_os as C
        e=self.s.propose_edit('context_policy',{'cache_compression_aggressiveness':.2},'save prefill')
        self.assertEqual(e['status'],'PENDING')
        with self.assertRaises(PermissionError):self.s.approve_edit(e['id'],authority='SELF')
        with self.assertRaises(PermissionError):self.s.propose_edit('hard_rules',{'x':1})
        done=self.s.approve_edit(e['id']);self.assertEqual(done['status'],'APPLIED')
        c=C.controller(self.r);self.assertEqual(c.knobs()['cache_compression_aggressiveness'],.2)
        self.assertEqual(self.s.rollback_edit(e['id'])['status'],'ROLLED_BACK');self.assertEqual(c.knobs()['cache_compression_aggressiveness'],C.CTX['cache_compression_aggressiveness'])
        other=self.s.propose_edit('replay_priority',{'family':'math','priority':.8});self.assertEqual(self.s.approve_edit(other['id'])['status'],'APPROVED_FOR_OWNER')
    def test_auto_self_edit_only_with_age_right_and_context_policy(self):
        self.s._allowed=lambda right:right=='safe_self_edit_without_dialog'
        self.assertEqual(self.s.propose_edit('context_policy',{'layout':'legacy'})['status'],'APPLIED')
        self.assertEqual(self.s.propose_edit('skill_metadata',{'a':1})['status'],'PENDING')
    def test_model_aggregates_and_fails_soft(self):
        m=self.s.model()
        for k in ('base','body','age','skills','tools','open_goals','learning','body_capabilities','memory_health','limits','corollary'):self.assertIn(k,m)
        self.assertIn('feeling',m['body']);self.assertEqual(m['memory_health']['dangling_sources'],0)
        self.assertIsNotNone(self.r.store.state('SELF_MODEL_N9:'+self.r.session,None)[0])

class RuntimeHookTests(Base):
    def test_turn_issues_corollary_and_attributes_own_outcome(self):
        import time
        from types import SimpleNamespace
        from unittest.mock import Mock
        def gen(messages,*a,**k):yield 'fine'
        self.r._route=Mock(return_value=('simple',{'source':'TEST_ROUTE_SEAM'}))
        self.r.pool.get=Mock(return_value=SimpleNamespace(role='C3_LANGUAGE',last_metrics={},generate=gen));self.r.learner.output_delta=Mock(return_value=None)
        self.r.submit('hello');until=time.monotonic()+10
        while not self.r.idle() and time.monotonic()<until:time.sleep(.005)
        row=self.r.last_answer();self.assertEqual(row['status'],'FINAL');meta=json.loads(row['metadata'])
        self.assertIn('feeling',meta['interoception'])
        cor=self.r.store.rows("SELECT payload FROM packets WHERE kind='SelfCorollary'");self.assertEqual(len(cor),1)
        att=[json.loads(x['payload']) for x in self.r.store.rows("SELECT payload FROM packets WHERE kind='SelfWorldAttribution'")]
        self.assertEqual({a['channel']:a['attribution'] for a in att}['action_status'],'SELF')
        op=Operator(self.r);self.assertIn('attribution_counts',op.run(':self status'));self.assertIn('feeling',op.run(':self body'))
        self.assertIn('models',op.run(':self'))  # bare :self keeps the F3 self_state view

if __name__=='__main__':unittest.main()
