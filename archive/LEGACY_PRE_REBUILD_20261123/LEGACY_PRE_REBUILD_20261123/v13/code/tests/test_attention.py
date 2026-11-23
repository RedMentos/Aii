"""WP-N5: F1 attention contract, thalamic gain, salience/caution separation, A4 salience. No models needed."""
import json
from pathlib import Path
import tempfile
import unittest
from v13.runtime import Runtime
from v13.operator import Operator
from v13 import attention as A
from v13 import neuromod as N
from v13.cognition import segments

class Base(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.r=Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled','off');self.n=N.Neuromod(self.r.store);self.a=A.Attention(self.r.store,None,self.n)
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def ev(self,text='x'):return self.r.store.event(self.r.session,text)['event_id']

class GainTests(Base):
    def test_salience_and_caution_are_separate_and_shape_couplings_differently(self):
        e=self.ev();out=self.a.modulate(e,sal={'conflict':1.})
        self.assertAlmostEqual(out['salience'],A.SAL['conflict'],6);self.assertEqual(out['caution'],0.)
        self.assertGreater(out['gains']['workspace'],A.GAIN['workspace']);self.assertEqual(out['gains']['action'],A.GAIN['action'])
        out=self.a.modulate(e,caut={'source_risk':1.})
        self.assertLess(out['gains']['action'],A.GAIN['action']);self.assertGreater(out['gains']['callosum'],A.GAIN['callosum'])
        self.assertEqual(out['truth_authority'],0)
    def test_gain_relaxes_to_base_per_experience_event(self):
        e=self.ev();g=self.a.modulate(e,sal={'goal_violation':1.})['gains']['focal']
        self.assertGreater(g,A.GAIN['focal'])
        for i in range(3):self.ev(str(i))
        self.assertAlmostEqual(self.a.gains()['focal']-A.GAIN['focal'],(g-A.GAIN['focal'])*A.RELAX**3,5)
        for i in range(60):self.ev('later '+str(i))
        self.assertAlmostEqual(self.a.gains()['focal'],A.GAIN['focal'],5)
    def test_gains_are_bounded_and_interrupt_needs_strong_salience(self):
        e=self.ev()
        for _ in range(20):out=self.a.modulate(e,sal={k:1. for k in A.SAL},caut={k:1. for k in A.CAUT})
        self.assertTrue(all(A.GAIN_MIN<=v<=A.GAIN_MAX for v in out['gains'].values()))
        self.assertTrue(out['interrupt']);self.assertEqual(out['interrupt_reason'],'external_interrupt')
        self.assertFalse(self.a.modulate(e,sal={'novelty':1.})['interrupt'])
    def test_neuromod_channels_map_onto_salience_and_caution(self):
        out=self.a.modulate(self.ev(),modulators={'world_prediction_error':1.,'novelty':.5})
        self.assertGreater(out['salience'],0);self.assertGreater(out['caution'],0)
        with self.assertRaises(ValueError):self.a.modulate(self.ev(),sal={'confidence':1.})
    def test_edges_and_restart(self):
        e=self.ev();self.a.modulate(e,sal={'conflict':1.})
        self.assertEqual(A.Attention(self.r.store).coupling('E_B1_B2'),self.a.gains()['callosum'])
        with self.assertRaises(ValueError):self.a.coupling('E_NOPE')

class AdmissionTests(Base):
    def test_budget_priority_and_canonical_statuses(self):
        e=self.ev()
        hi=self.a.request(e,'JEF','MEMORY','recall',priority=.9,budget=600)
        lo=self.a.request(e,'B1','A_SOURCE','exactness',priority=.2,budget=600)
        small=self.a.request(e,'SALIENCE','WORLD','conflict',priority=.5,budget=100)
        res={x['request_packet_id']:x for x in self.a.admit(e,[lo,hi,small],budget=1024)}
        self.assertEqual(res[hi['packet_id']]['status'],'GRANTED');self.assertEqual(res[hi['packet_id']]['delivery'],'exact_memory')
        self.assertEqual(res[small['packet_id']]['status'],'GRANTED');self.assertEqual(res[lo['packet_id']]['status'],'TOO_EXPENSIVE')
        self.assertEqual(res[lo['packet_id']]['granted_budget'],0)
    def test_pressure_shrinks_budget_and_providers_can_refuse(self):
        e=self.ev();r=self.a.request(e,'JEF','MEMORY','recall',budget=300)
        self.assertEqual(self.a.admit(e,[r],budget=1024,pressure=1.)[0]['status'],'TOO_EXPENSIVE')
        out=self.a.admit(e,[r],providers={'MEMORY':lambda q:None})[0];self.assertEqual((out['status'],out['detail']),('NOT_AVAILABLE','empty'))
        out=self.a.admit(e,[r],providers={})[0];self.assertEqual(out['detail'],'no_provider')
        out=self.a.admit(e,[r],providers={'MEMORY':lambda q:{'memory_id':'m1'}})[0]
        self.assertEqual(out['status'],'GRANTED');self.assertEqual(out['payload'],{'memory_id':'m1'})
    def test_expired_foreign_and_teacher_rules(self):
        e=self.ev();other=self.ev('other')
        old=self.a.request(e,'JEF','B2','goal',expires_at=1.)
        foreign=self.a.request(other,'JEF','B2','goal')
        t=self.a.request(e,'TEACHER','A_SOURCE','novelty',priority=1.,resolution='teacher_view')
        self.assertLessEqual(t['priority'],A.A4['teacher_hint_gain'])
        with self.assertRaises(ValueError):self.a.request(e,'JEF','A_SOURCE','novelty',resolution='teacher_view')
        res={x['request_packet_id']:x for x in self.a.admit(e,[old,foreign,t])}
        self.assertEqual(res[old['packet_id']]['detail'],'expired');self.assertEqual(res[foreign['packet_id']]['detail'],'other_event')
        self.assertEqual(res[t['packet_id']]['status'],'GRANTED');self.assertTrue(res[t['packet_id']]['teacher_tagged'])
        class Older:
            def system_stage(self):return 1
        self.assertEqual(A.Attention(self.r.store,Older()).admit(e,[t])[0]['detail'],'teacher_view_age0_only')
    def test_contract_rejects_bad_requests(self):
        e=self.ev()
        for args in [('X','B1','goal'),('JEF','BRAIN','goal'),('JEF','B1','because')]:
            with self.assertRaises(ValueError):self.a.request(e,*args)
        with self.assertRaises(ValueError):self.a.request(e,'JEF','B1','goal',budget=0)

class LearningTests(Base):
    def test_grant_touches_eligibility_and_outcome_modulates_policy_path(self):
        e=self.ev();r=self.a.request(e,'JEF','MEMORY','recall',priority=.8);resp=self.a.admit(e,[r])[0]
        g=self.n.gate(A.PATH);self.assertGreater(g['eligibility'],0)
        q=self.a.outcome(resp['packet_id'],1.);self.assertEqual(q['key'],'recall|MEMORY');self.assertGreater(q['mean'],0)
        self.assertGreater(self.n.gate(A.PATH)['modulator']['instrumental'],0)
        with self.assertRaises(ValueError):self.a.outcome(resp['packet_id'],1.)
    def test_learned_prior_is_shadow_until_explicit_human_switch(self):
        for _ in range(5):
            e=self.ev();w=self.a.request(e,'JEF','WORLD','verify',priority=.5);b=self.a.request(e,'JEF','B1','verify',priority=.5)
            for x in self.a.admit(e,[w,b]):self.a.outcome(x['packet_id'],1. if x['request_packet_id']==w['packet_id'] else -1.)
        e=self.ev();w=self.a.request(e,'JEF','WORLD','verify',priority=.5);b=self.a.request(e,'JEF','B1','verify',priority=.5)
        res={x['request_packet_id']:x for x in self.a.admit(e,[w,b])}
        self.assertEqual(res[w['packet_id']]['score'],res[w['packet_id']]['scaffold_score'])
        self.assertGreater(res[w['packet_id']]['learned_shadow'],0);self.assertLess(res[b['packet_id']]['learned_shadow'],0)
        with self.assertRaises(PermissionError):self.a.set_mode('ACTIVE','SYSTEM')
        self.a.set_mode('ACTIVE','EXPLICIT_HUMAN');res={x['request_packet_id']:x for x in self.a.admit(e,[w,b])}
        self.assertGreater(res[w['packet_id']]['score'],res[w['packet_id']]['scaffold_score'])
        self.assertLess(res[b['packet_id']]['score'],res[b['packet_id']]['scaffold_score'])
        self.assertLessEqual(res[w['packet_id']]['score'],res[w['packet_id']]['scaffold_score']*(1+A.LEARNED_MAX)+1e-5)

class PerceptionTests(Base):
    def test_a4_never_drops_a_chunk_and_requests_bounded_highres(self):
        text=('The weather was pleasant and calm all afternoon. '*4+'Invoice 4471 says not 30 but 45 EUR, due 2026-11-02? ')*3
        e=self.ev(text);src={'source_id':'s','sha256':'0','char_start':0,'char_end':len(text),'modality':'text'}
        segs=segments(text,src,60);out=self.a.perceive(e,segs,goal='When is the invoice due and how much?')
        self.assertEqual(len(out['segments']),len(segs))
        self.assertTrue(all(r['recoverable'] and r['suppression']<=A.A4['suppression_max'] for r in out['segments']))
        self.assertLessEqual(len(out['highres']),A.A4['max_highres_regions'])
        top=max(out['segments'],key=lambda r:r['score']);self.assertIn('4471',segs[top['index']]['text']+segs[min(top['index']+1,len(segs)-1)]['text'])
        self.assertTrue(all(q['requester']=='A4' and q['target']=='A_SOURCE' for q in out['requests']))
        self.assertAlmostEqual(sum(r['weight'] for r in out['segments']),1.,5)
    def test_teacher_hint_is_capped(self):
        e=self.ev();src={'source_id':'s','sha256':'0','char_start':0,'char_end':5,'modality':'text'}
        out=self.a.perceive(e,[{'text':'hello','source_ref':src}],teacher_hints={0:1.},file_requests=False)
        self.assertEqual(out['segments'][0]['teacher_hint'],A.A4['teacher_hint_gain'])

class InterfaceTests(Base):
    def test_rank_for_focal_loop_and_offer_features(self):
        ranked=self.a.rank([{'id':'a','kind':'B1','priority':.2,'salience':.1},{'id':'b','kind':'B2','priority':.9,'salience':.6}])
        self.assertEqual([c['id'] for c in ranked],['b','a']);self.assertIn('admission_score',ranked[0])
        f=A.offer_features({'packet_id':'p','role':'B1_DETAIL','evidence_refs':[{}],'offer':{'needs_reentry':True,'uncertainty':'x','summary':'s','quotes':[]}})
        self.assertEqual(f['kind'],'B1');self.assertAlmostEqual(f['salience'],A.SAL['conflict'],6);self.assertTrue(f['needs_reentry'])
    def test_operator(self):
        op=Operator(self.r);self.assertIn(A.REVISION,op.run(':attention status'))
        self.assertIn('"gain"',op.run(':attention edge E_C4_C5'));self.assertIn('ACTIVE',op.run(':attention active'))

class LiveHookTests(Base):
    """WP-N5 live-hook rest: N10 modulators -> gain, A4 re-look outcome, action gain into C5."""
    def test_recent_modulators_feed_gain_decayed_and_session_scoped(self):
        e1=self.ev('a');self.n.signal(e1,surprise=1.,novelty=.4,task_success=1.)
        e2=self.ev('b');ch=self.a.recent_modulators(e2,self.r.session)
        self.assertAlmostEqual(ch['surprise'],1.,6);self.assertNotIn('action_error',ch)
        self.n.signal(e2,world_prediction_error=.5);e3=self.ev('c');ch=self.a.recent_modulators(e3,self.r.session)
        self.assertAlmostEqual(ch['surprise'],A.RELAX,6);self.assertAlmostEqual(ch['world_prediction_error'],.5,6)
        self.assertEqual(self.a.recent_modulators(e3,'other-session'),{})
        self.assertEqual(self.a.recent_modulators(e1,self.r.session),{})  # own event never feeds itself
        out=self.a.modulate(e3,modulators=ch);self.assertGreater(out['salience'],0);self.assertGreater(out['caution'],0)
    def test_cue_coverage_labels_only_spans_with_exact_cues(self):
        self.assertIsNone(A.coverage('the weather was calm','anything'))
        self.assertEqual(A.coverage('Invoice 4471 says not 30','It is 4471, not 30.'),1.)
        self.assertEqual(A.coverage('Invoice 4471 says not 30','It is 31.'),0.)
        self.assertAlmostEqual(A.coverage('call "Anna Berg" at 5','Anna Berg called'),.5)
    def test_source_outcome_books_once_and_updates_policy(self):
        text='Calm intro sentence here. Invoice 4471 says not 30 but 45 EUR.';e=self.ev(text)
        src={'source_id':'s','sha256':'0','char_start':0,'char_end':len(text),'modality':'text'}
        out=self.a.perceive(e,segments(text,src,30),goal='How much is invoice 4471?')
        self.assertTrue(out['requests'])
        self.a.admit(e,out['requests'],providers={'A_SOURCE':lambda r:{'source_ref':r['source_ref']}})
        done=self.a.source_outcome(e,text,'Invoice 4471 is 45 EUR, not 30.')
        self.assertTrue(done);self.assertTrue(all(d['key'].endswith('|A_SOURCE') for d in done))
        self.assertEqual(self.a.source_outcome(e,text,'again'),[])  # booked once
        pol=self.a.report()['policy'];self.assertTrue(any(k.endswith('|A_SOURCE') and v['n']>=1 for k,v in pol.items()))
    def test_action_gain_scales_c5_focal_support(self):
        from v13.focal import ActionGate
        e=self.r.store.event(self.r.session,'x');coal=[{'item_id':'o','source_kind':'B1_DETAIL','priority':1.}]
        base=ActionGate(self.r.store).select(e,route='simple',direct=False,resource_state='NORMAL',coalition=coal)
        low=ActionGate(self.r.store).select(e,route='simple',direct=False,resource_state='NORMAL',coalition=coal,gain_action=A.GAIN_MIN)
        import json as J
        pk=lambda pid:J.loads(self.r.store.one("SELECT payload FROM packets WHERE id=?",(pid,))['payload'])
        b=pk(base['packet_id']);l=pk(low['packet_id'])
        sb={c['action_id']:c['score'] for c in b['candidates']};sl={c['action_id']:c['score'] for c in l['candidates']}
        self.assertLess(sl['B1_DETAIL'],sb['B1_DETAIL']);self.assertLess(l['action_gain'],b['action_gain'])
    def test_live_turn_runs_attention_hooks(self):
        text='Copy exactly: Invoice 4471 says not 30 but 45 EUR, due 2026-11-02?'
        ev=self.r.store.event(self.r.session,text);e=ev['event_id'];self.r._turn(ev)
        sel=[json.loads(r['payload']) for r in self.r.store.rows("SELECT payload FROM packets WHERE kind='ActionSelection' AND event_id=?",(e,))]
        self.assertTrue(sel);self.assertIn('action_gain',sel[-1])
        reqs=self.r.store.rows("SELECT payload FROM packets WHERE kind='AttentionRequest' AND event_id=?",(e,))
        self.assertTrue(reqs)
        self.assertIsNone(self.r.store.one("SELECT id FROM telemetry WHERE kind='attention_unavailable'"))

if __name__=='__main__':unittest.main()
