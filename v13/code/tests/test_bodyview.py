"""WP-T5 body view: B1 detail windows from granted A4 spans, B5 state as a source, B4 cross-session context (fixtures)."""
import json
from pathlib import Path
import tempfile
import unittest
from v13 import bodyview
from v13.attention import controller as attention
from v13.contracts import packet
from v13.operator import Operator
from v13.runtime import Runtime

LONG=('Intro sentence about the house. '*12)+'The rent is 1,250 euros per month and is due on the 3rd. '+('Filler about the garden. '*12)+'Heating costs 90 euros. '+('More filler text here. '*10)

class Base(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name))
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def grant(self,e,phrase):
        ref=e['source_ref'];i=LONG.index(phrase);a=attention(self.r)
        req=a.request(e['event_id'],'A4','A_SOURCE','exactness',priority=.9,budget=16,source_ref=ref|{'char_start':ref['char_start']+i,'char_end':ref['char_start']+i+len(phrase)})
        return a.admit(e['event_id'],[req],providers={'A_SOURCE':lambda r:{'source_ref':r['source_ref']}})[0]

class DetailWindows(Base):
    def test_windows_are_exact_padded_and_merged(self):
        e=self.r.store.event(self.r.session,LONG);text=self.r.store.read_source(e['source_ref'])
        self.assertEqual(bodyview.detail_windows(self.r.store,e['event_id'],text,e['source_ref']),[])
        self.assertEqual(self.grant(e,'1,250 euros')['status'],'GRANTED');self.grant(e,'due on the 3rd')
        w=bodyview.detail_windows(self.r.store,e['event_id'],text,e['source_ref'])
        self.assertEqual(len(w),1)  # overlapping spans merge
        self.assertIn('1,250 euros',w[0]['text']);self.assertIn('due on the 3rd',w[0]['text']);self.assertGreater(len(w[0]['text']),240)
        self.assertEqual(self.r.store.read_source(w[0]['source_ref']),w[0]['text'])  # exact SourceRef
        self.grant(e,'Heating costs');w=bodyview.detail_windows(self.r.store,e['event_id'],text,e['source_ref'])
        self.assertLessEqual(sum(len(x['text']) for x in w),bodyview.MAX_CHARS)

class StateAndB4(Base):
    def test_body_state_is_a_source_and_can_be_switched_off(self):
        e=self.r.store.event(self.r.session,'Plan the week');self.r.world.self_state()
        bs=bodyview.body_state(self.r,e,'B2_GIST','Plan the week')
        self.assertEqual(bs['view']['authority'],'STATE_NOT_FACT');self.assertEqual(json.loads(self.r.store.read_source(bs['source_ref']))['self']['learning'],self.r.cfg['learning_mode'])
        Operator(self.r).run(':bodyview state off');self.assertIsNone(bodyview.body_state(self.r,e,'B2_GIST','x'))
        with self.assertRaises(ValueError):Operator(self.r).run(':bodyview b4 maybe')
    def offer(self,e,summary):
        p=packet('OfferPacket','B2_GIST',e['event_id'],e['brain_generation_id'],[e['source_ref']],role='B2_GIST',based_on_state_version=0,deadline_monotonic_ns=1,
                 evidence_refs=[],offer={'summary':summary,'quotes':[],'uncertainty':'low','needs_reentry':False},confidence=0.,rejected_quotes=0,model_revision=self.r.models.revision('B2_GIST'))
        self.r.store.add_packet('OfferPacket',p);return p
    def test_b4_only_coalition_offers_on_the_same_topic_and_shadow_by_default(self):
        r=self.r;old=r.session;e0=r.store.event(old,'Project Aurora budget is tight this quarter')
        p=self.offer(e0,'Aurora budget tight');other=self.offer(r.store.event(old,'Project Zephyr launch'),'Zephyr launch')
        r.session=r.store.new_session('B4 test');e=r.store.event(r.session,'What about project Aurora costs?')
        self.assertEqual(bodyview.cross_session(r,e,'B2_GIST','What about project Aurora costs?',[],4000),[])  # not in a coalition yet
        orig=r.store.one
        r.store.one=lambda sql,args=():{'1':1} if "kind='FocalItem'" in sql and args==(p['packet_id'],) else (None if "kind='FocalItem'" in sql else orig(sql,args))
        try:
            self.assertEqual(bodyview.cross_session(r,e,'B2_GIST','What about project Aurora costs?',[],4000),[])  # SHADOW: logged only
            Operator(r).run(':bodyview b4 on')
            got=bodyview.cross_session(r,e,'B2_GIST','What about project Aurora costs?',[],4000)
            self.assertEqual([g['offer_id'] for g in got],[p['packet_id']]);self.assertTrue(got[0]['native_context']['cross_session'])
            self.assertEqual(bodyview.cross_session(r,e,'B1_DETAIL','x',[],4000),[])
            self.assertEqual(bodyview.cross_session(r,e,'B2_GIST','What about project Zephyr?',[],4000),[])  # Zephyr offer never reached a coalition
        finally:r.store.one=orig

class OfferQuery(Base):
    def test_b1_query_gets_windows_and_state_with_provenance(self):
        import time
        from types import SimpleNamespace
        from unittest.mock import Mock
        e=self.r.store.event(self.r.session,LONG);self.grant(e,'1,250 euros');seen={}
        def generate(messages,*a,**k):
            seen['q']=json.loads(messages[1]['content']);return iter([json.dumps({'summary':'Rent 1,250','quotes':['1,250 euros'],'uncertainty':'low','needs_reentry':False})])
        self.r.pool.get=Mock(return_value=SimpleNamespace(role='B1_DETAIL',last_metrics={},generate=generate))
        p=self.r.cognition.offer('B1_DETAIL',e,0,time.monotonic()+30)
        self.assertIn('1,250 euros',seen['q']['detail_windows'][0]);self.assertEqual(seen['q']['body_state']['authority'],'STATE_NOT_FACT')
        q=json.loads(self.r.store.one("SELECT payload FROM packets WHERE kind='QueryPacket' ORDER BY rowid DESC LIMIT 1")['payload'])
        self.assertEqual(q['bodyview']['detail_windows'],1);self.assertIn(q['bodyview']['body_state_ref'],q['provenance'])
        self.assertEqual(len(p['evidence_refs']),1)  # the quote verifies against the exact source

if __name__=='__main__':unittest.main()
