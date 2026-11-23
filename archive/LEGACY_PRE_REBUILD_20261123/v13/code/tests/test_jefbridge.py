"""WP-N3: JEF broadcast cache, JEF2B bridge gate, offer-utility learning, top-down query values, observer-pass utility."""
import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from v13.runtime import Runtime
from v13.operator import Operator
from v13.contracts import packet
from v13 import jefbridge as J
from v13 import neuromod as N

class Base(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.r.sleep.cycle.set_policy('enabled','off')
        self.n=N.Neuromod(self.r.store);self.j=J.JEFBridge(self.r.store,self.r.cfg,self.n)
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def event(self,text='Compare the train times 08:15 and 09:40'):
        eid=self.r.store.event(self.r.session,text)['event_id']
        return {'event_id':eid,'brain_generation_id':self.r.store.generation_id,'source_ref':self.r.store.source(text)}
    def offer(self,e,role,summary,needs=False,unc='',refs=0):
        p=packet('OfferPacket',role,e['event_id'],e['brain_generation_id'],[e['source_ref']],role=role,based_on_state_version=1,deadline_monotonic_ns=1,
                 evidence_refs=[e['source_ref']]*refs,offer={'summary':summary,'quotes':[],'uncertainty':unc,'needs_reentry':needs},confidence=.6)
        return self.r.store.add_packet('OfferPacket',p)
    def broadcast(self,e,version=1):
        return self.r.store.add_packet('JEFBroadcastPacket',packet('JEFBroadcastPacket','C1_EXEC',e['event_id'],e['brain_generation_id'],[e['source_ref']],
            state_version=version,goal='Compare the train times',constraints=['be exact'],source_refs=[e['source_ref']]))

class CacheTests(Base):
    def test_broadcast_cache_is_small_versioned_and_marked_symbolic(self):
        e=self.event();b=self.broadcast(e);p=self.j.broadcast_cache(e,b,{'open_questions':[1]},['slot1'],{'x':1},'calm')
        c=p['cache'];self.assertEqual(c['state_version'],1);self.assertEqual(len(c['goal_latent']),J.DIM);self.assertEqual(c['latent_kind'],'HASHED_SYMBOLIC_NOT_NATIVE')
        self.assertLess(p['size_bytes'],4096);self.assertEqual(c['focal_slot_refs'],['slot1'])
        self.assertAlmostEqual(sum(x*x for x in c['goal_latent']),1.,2)
        self.assertEqual(J.hashed_latent('same words here'),J.hashed_latent('here same words'))
    def test_bridge_view_shadow_empty_active_explores_and_rejects_stale(self):
        e=self.event();b=self.broadcast(e);self.j.broadcast_cache(e,b)
        self.assertEqual(self.j.bridge_view('B1_DETAIL',e,1),({},[]))
        self.j.set_mode('ACTIVE','EXPLICIT_HUMAN');extra,chosen=self.j.bridge_view('B1_DETAIL',e,1)
        self.assertEqual(sorted(extra),sorted(chosen));self.assertTrue(set(chosen)<=set(J.EXTRA_FIELDS))
        self.assertEqual(self.j.bridge_view('B1_DETAIL',e,2),({},[]))  # stale state_version is never used
        with self.assertRaises(PermissionError):self.j.set_mode('ACTIVE')
    def test_learned_bridge_field_is_kept_when_it_helps(self):
        self.j.set_mode('ACTIVE','EXPLICIT_HUMAN')
        def fn(st):st['fields']['B1_DETAIL|body_state']={'with':[4.,5],'without':[1.,5]}
        self.j._mutate(fn)
        for i in range(6):
            e=self.event('q %d'%i);self.j.broadcast_cache(e,self.broadcast(e))
            self.assertIn('body_state',self.j.bridge_view('B1_DETAIL',e,1)[1])

class LearningTests(Base):
    def test_offer_model_learns_which_offers_help(self):
        for i in range(40):
            e=self.event('Compare the train times 08:15 and 09:40 run %d'%i)
            good=self.offer(e,'B1_DETAIL','The 08:15 train is faster than the 09:40 train',refs=2)
            bad=self.offer(e,'B2_GIST','Weather mood poem',needs=True,unc='maybe unsure')
            run={'coalition':[{'item_id':good['packet_id']}],'inquisition':[],'decision':'INCORPORATE_A','trajectory':[{'view':{'conflict':0.,'uncertainty':.2}}]}
            p=self.j.learn_turn(e,'Compare the train times',[good,bad],'The 08:15 train is faster than the 09:40 train.',run,[good['packet_id'],bad['packet_id']],1.2)
        pred={o['role']:o['predicted'] for o in p['offers']}
        self.assertGreater(pred['B1_DETAIL'],pred['B2_GIST']);self.assertEqual(p['learned_decision'],'INCORPORATE_A')
        rep=self.j.report();self.assertEqual(rep['scaffold_agreement'] is not None,True);self.assertIn('AB',rep['observer_utility'])
        self.assertGreater(rep['observer_utility']['AB']['unnecessary_per_turn'],0)
        traces=self.r.store.rows("SELECT payload FROM packets WHERE kind='LearningTrace'")
        self.assertTrue(any(json.loads(t['payload'])['path_id']=='jef_offer_utility' for t in traces));self.assertEqual(N.kind_of('jef_offer_utility'),'control')
    def test_offer_utility_hook_shadow_unchanged_active_bounded(self):
        e=self.event();o=self.offer(e,'B1_DETAIL','x',refs=2)
        self.assertEqual(self.j.offer_utility(o,.4),.4)
        def fn(st):st['w']=[5.]*len(J.FEATURES);st['updates']=J.MIN_UPDATES
        self.j._mutate(fn);self.assertEqual(self.j.offer_utility(o,.4),.4)
        self.j.set_mode('ACTIVE','EXPLICIT_HUMAN');u=self.j.offer_utility(o,.4)
        self.assertGreater(u,.4);self.assertLessEqual(u,.4+J.LEARNED_MAX+1e-9)
    def test_reentry_value_drives_query_recommendation(self):
        for i in range(4):
            e=self.event('turn %d'%i);first=self.offer(e,'B2_GIST','gist only')
            re_a=self.offer(e,'B1_DETAIL','exact 08:15 detail',refs=1)
            run={'coalition':[{'item_id':re_a['packet_id']}],'inquisition':[],'decision':'QUERY_A','trajectory':[{'view':{'conflict':.8,'uncertainty':.5}}]}
            self.j.learn_turn(e,'g',[first,re_a],'exact 08:15 detail',run,[first['packet_id']])
            e=self.event('turn b %d'%i);first=self.offer(e,'B1_DETAIL','detail first');re_b=self.offer(e,'B2_GIST','unhelpful gist')
            run={'coalition':[],'inquisition':[],'decision':'QUERY_B','trajectory':[{'view':{'conflict':.8,'uncertainty':.5}}]}
            self.j.learn_turn(e,'g',[first,re_b],'nothing alike',run,[first['packet_id']])
        rec=self.j.recommend_query({'conflict':.9,'uncertainty':.5})
        self.assertEqual((rec['target'],rec['desired_scale'],rec['learned'],rec['conflict_to_resolve']),('B1_DETAIL','fine',True,True))
    def test_human_rating_updates_selected_offers(self):
        e=self.event();o=self.offer(e,'B1_DETAIL','alpha beta gamma',refs=1)
        self.j.learn_turn(e,'g',[o],'unrelated words',{'coalition':[{'item_id':o['packet_id']}]},[o['packet_id']])
        before=self.j.report()['updates'];out=self.j.outcome(e['event_id'],1.)
        self.assertEqual(out,{'updated_offers':1});self.assertEqual(self.j.report()['updates'],before+1)
        self.assertEqual(self.j.outcome('nope',1.),{'updated_offers':0})

class RuntimeTests(Base):
    def test_turn_writes_cache_and_bridge_turn(self):
        def gen(messages,*a,**k):yield 'fine'
        self.r._route=Mock(return_value=('simple',{'source':'TEST_ROUTE_SEAM'}))
        self.r.pool.get=Mock(return_value=SimpleNamespace(role='C3_LANGUAGE',last_metrics={},generate=gen));self.r.learner.output_delta=Mock(return_value=None)
        self.r.submit('hello there');until=time.monotonic()+10
        while not self.r.idle() and time.monotonic()<until:time.sleep(.005)
        self.assertEqual(self.r.last_answer()['status'],'FINAL')
        self.assertEqual(len(self.r.store.rows("SELECT id FROM packets WHERE kind='JEFBroadcastCache'")),1)
        t=json.loads(self.r.store.one("SELECT payload FROM packets WHERE kind='JEFBridgeTurn'")['payload'])
        self.assertEqual(t['observer_mode'],'none');self.assertEqual(t['mode'],'SHADOW')
        op=Operator(self.r);self.assertIn('observer_utility',op.run(':jef'));self.assertIn('desired_scale',op.run(':jef query'))

class FocalHookTests(Base):
    def learn_b1_wins(self):
        for i in range(4):
            e=self.event('turn %d'%i);first=self.offer(e,'B2_GIST','gist only');re_a=self.offer(e,'B1_DETAIL','exact 08:15 detail',refs=1)
            self.j.learn_turn(e,'g',[first,re_a],'exact 08:15 detail',{'coalition':[{'item_id':re_a['packet_id']}],'inquisition':[],'trajectory':[{'view':{'conflict':.8}}]},[first['packet_id']])
            e=self.event('turn b %d'%i);first=self.offer(e,'B1_DETAIL','detail first');re_b=self.offer(e,'B2_GIST','unhelpful gist')
            self.j.learn_turn(e,'g',[first,re_b],'nothing alike',{'coalition':[],'inquisition':[],'trajectory':[{'view':{'conflict':.8}}]},[first['packet_id']])
    def test_query_target_logs_in_shadow_and_steers_only_in_active_once_learned(self):
        from v13.focal import FocalLoop
        view={'conflict':.9,'uncertainty':.5};self.r.jefbridge=self.j
        t,info=self.j.query_target(view,'B2_GIST');self.assertEqual(t,'B2_GIST');self.assertFalse(info['learned'])  # no evidence yet
        self.learn_b1_wins()
        t,info=FocalLoop(self.r)._jef_target(view,'B2_GIST')
        self.assertEqual((t,info['learned_target'],info['applied'],info['mode']),('B2_GIST','B1_DETAIL',False,'SHADOW'))
        self.j.set_mode('ACTIVE','EXPLICIT_HUMAN');t,info=FocalLoop(self.r)._jef_target(view,'B2_GIST')
        self.assertEqual((t,info['applied']),('B1_DETAIL',True))
        self.assertEqual(self.j.query_target(view,'B1_DETAIL')[1]['applied'],False)  # agreement is not an override
        self.assertEqual(self.j.query_target({'conflict':0.},'B2_GIST')[0],'B2_GIST')  # calm trigger has no evidence
    def test_observer_scale_lowers_time_only_with_evidence_and_in_active(self):
        self.assertEqual(self.j.observer_scale('detail')['reason'],'TOO_FEW');self.assertIsNone(self.j.observer_scale('none')['mode'])
        for i in range(J.OBS_MIN_N):  # B1 observer alone, its offer never helps the answer
            e=self.event('obs %d'%i);a=self.offer(e,'B1_DETAIL','irrelevant musings about weather')
            self.j.learn_turn(e,'g',[a],'the train leaves at 08:15',{'coalition':[],'inquisition':[]},[a['packet_id']])
        o=self.j.observer_scale('detail');self.assertEqual((o['mode'],o['applied'],o['scale']),('A',False,J.OBS_FLOOR))
        self.j.set_mode('ACTIVE','EXPLICIT_HUMAN');self.assertTrue(self.j.observer_scale('detail')['applied'])
        self.assertEqual(self.j.observer_scale('gist')['scale'],1.)

if __name__=='__main__':unittest.main()
