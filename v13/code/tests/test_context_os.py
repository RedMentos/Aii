"""WP-N7: Context OS layers, exact-span compression, exact restore, cache layout, warm memory, knob guard. No models."""
import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from v13.runtime import Runtime
from v13.operator import Operator
from v13 import context_os as C
from v13 import neuromod as N

def rows(*turns):
    out=[]
    for i,(u,a) in enumerate(turns):
        out+= [{'event_id':'ev%d'%i,'role':'user','text':u},{'event_id':'ev%d'%i,'role':'assistant','text':a}]
    return out

LONG='We talked about the garden and the weather for a long while. '*6

class Base(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.r=Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled','off');self.n=N.Neuromod(self.r.store);self.c=C.ContextOS(self.r.store,self.r.cfg,None,self.n)
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def ev(self,text='x'):return self.r.store.event(self.r.session,text)['event_id']
    def plan(self,query,history,volatile=None,**kw):
        return self.c.plan(self.ev(query),'C3_LANGUAGE','SYS',volatile if volatile is not None else [('LATENT_STATE','\nTASK:',{'task_request':None})],history,query,**kw)

class CompressionTests(unittest.TestCase):
    def test_compression_keeps_every_exact_span_and_is_shorter(self):
        text='The invoice total was 1,234.50 EUR on 2026-10-09, see https://x.org/a and run `pip install foo`. '+LONG
        out,spans,ok=C.compress(text,140)
        self.assertTrue(ok);self.assertLess(len(out),len(text))
        for s in ['1,234.50','2026-10-09','https://x.org/a','`pip install foo`']:self.assertIn(s,spans);self.assertIn(s,out)
    def test_too_many_spans_or_no_gain_stays_raw(self):
        text=' '.join(str(i)+'x' for i in range(40))
        self.assertFalse(C.compress(text,140)[2]);self.assertFalse(C.compress('short.',140)[2])
    def test_exact_need_triggers(self):
        self.assertEqual(C.exact_need('hello there')[0],0.)
        self.assertIn('literal',C.exact_need('Quote it word for word')[1]);self.assertIn('numbers',C.exact_need('what was the 42?')[1])
        self.assertIn('conflict',C.exact_need('hi',['CONTESTED'])[1]);self.assertIn('source_critique',C.exact_need('Laut welcher Quelle?')[1])

class PlanTests(Base):
    def test_shadow_returns_legacy_messages_byte_identical(self):
        hist=rows(('a? '+LONG,'b. '+LONG),('c?','d.'))
        vol=[('ACTIVE_VIEW','\nMEM:',[{'topic':'t','correction':'v'}]),('LATENT_STATE','\nTASK:',{'task_request':None})]
        out=self.plan('next?',hist,vol)
        legacy=[{'role':'system','content':'SYS\nMEM:'+json.dumps([{'topic':'t','correction':'v'}],ensure_ascii=False,separators=(',',':'))+'\nTASK:'+json.dumps({'task_request':None},separators=(',',':'))}]
        self.assertFalse(out['applied']);self.assertEqual(out['messages'],out['legacy'])
        self.assertEqual(out['legacy'][0]['content'],self.c.plan(self.ev('q'),'C3_LANGUAGE','SYS',vol,[],'q')['legacy'][0]['content'])
        self.assertEqual([m['role'] for m in out['legacy']],['system','user','assistant','user','assistant','user'])
        self.assertEqual(out['plan']['mode'],'SHADOW')
    def test_oldest_unpinned_turn_is_compressed_newest_stays_raw(self):
        hist=rows(*[('Question %d about plants. '%i+LONG[:180],'Answer %d. '%i+LONG[:180]) for i in range(10)])
        out=self.plan('anything new?',hist);forms=[x['form'] for x in out['plan']['items'] if x['item_id'].startswith('ev')]
        self.assertEqual(forms[0],'COMPRESSED');self.assertEqual(forms[-1],'RAW');self.assertIn('compress',out['plan']['decisions'])
        self.assertEqual(out['plan']['exact']['span_recall'],1.)
        planned=out['planned'];self.assertTrue(planned[1]['content'].startswith('[compressed earlier turn'))
        self.assertEqual([m['role'] for m in planned][:3],['system','user','assistant'])
    def test_exact_need_restores_relevant_turn(self):
        hist=rows(('What is the gate code for the garden shed? '+LONG,'The shed code is 4471. '+LONG),*[('Other %d. '%i+LONG,'Ok %d. '%i+LONG) for i in range(4)])
        out=self.plan('Tell me the garden shed gate code exactly',hist)
        first=[x for x in out['plan']['items'] if x['item_id']=='ev0'][0]
        self.assertTrue(first['restored']);self.assertEqual(first['form'],'RAW');self.assertIn('restore',out['plan']['decisions'])
        self.assertGreaterEqual(out['plan']['exact']['need'],out['plan']['exact']['threshold'])
    def test_budget_pressure_points_old_turns_but_never_drops_newest(self):
        self.c.cfg=dict(self.r.cfg,context_tokens=600,answer_tokens=64)
        hist=rows(*[('Q %d '%i+LONG*3,'A %d '%i+LONG*3) for i in range(6)])
        out=self.plan('go on',hist);items={x['item_id']:x for x in out['plan']['items']}
        self.assertEqual(items['ev0']['layer'],'SOURCE_LINKS');self.assertNotEqual(items['ev5']['form'],'POINTER')
        self.assertLess(out['plan']['exact']['span_recall'],1.)  # numbers in pointed turns are out of view -> measured
    def test_volatile_lists_are_compacted_to_the_global_share(self):
        self.c.cfg=dict(self.r.cfg,context_tokens=300,answer_tokens=32)
        vol=[('ACTIVE_VIEW','\nMEM:',[{'correction':'x'*200} for _ in range(6)]),('LATENT_STATE','\nTASK:',{'t':1})]
        out=self.plan('q',[],vol);mem=[x for x in out['plan']['items'] if x['layer']=='ACTIVE_VIEW'][0]
        self.assertGreater(mem['pointers'],0);self.assertIn('compact_active_view',out['plan']['decisions'])
        self.assertIn('"t":1',out['planned'][0]['content'])  # latent state is never dropped
    def test_stable_prefix_needs_declared_capability_and_reuses_prefix(self):
        hist=rows(('a','b'))
        vol=[('ACTIVE_VIEW','\nMEM:',['m1']),('LATENT_STATE','\nTASK:',{'n':1})]
        out=self.plan('q1',hist,vol);self.assertEqual(out['plan']['layout'],'legacy');self.assertEqual(out['plan']['cache']['fallback_reason'],'template_capability_unknown')
        self.c.set_capability('C3_LANGUAGE','consecutive_user',True);self.c.set_layout('stable_prefix')
        out=self.plan('q1',hist,vol);self.assertEqual(out['plan']['layout'],'stable_prefix')
        self.assertEqual(out['planned'][0]['content'],'SYS');self.assertEqual(out['planned'][-1],{'role':'user','content':'q1'})
        self.assertTrue(out['planned'][-2]['content'].startswith(C.VOLATILE_HEAD))
        vol2=[('ACTIVE_VIEW','\nMEM:',['m2']),('LATENT_STATE','\nTASK:',{'n':2})]
        nxt=self.plan('q2',hist+rows(('q1','r1'))[0:0],vol2);cache=nxt['plan']['cache']
        self.assertGreater(cache['est_reused_chars_planned'],cache['est_reused_chars_legacy'])  # volatile change breaks legacy at msg 0
    def test_append_only_reenters_transcript_and_falls_back_on_mismatch(self):
        self.c.set_capability('C3_LANGUAGE','consecutive_user',True);self.assertEqual(self.c.report()['layout'],'append_only')
        vol=lambda i:[('LATENT_STATE','\nTASK:',{'n':i})]
        e1=self.ev('q1');p1=self.c.plan(e1,'C3_LANGUAGE','SYS',vol(1),[],'q1')
        self.assertEqual(p1['plan']['cache']['fallback_reason'],'append_no_matching_transcript')
        hist=[{'event_id':e1,'role':'user','text':'q1'},{'event_id':e1,'role':'assistant','text':'a1'}]
        e2=self.ev('q2');p2=self.c.plan(e2,'C3_LANGUAGE','SYS',vol(2),hist,'q2')
        self.assertIn('append_reentry',p2['plan']['decisions']);self.assertEqual(p2['planned'][:len(p1['planned'])],p1['planned'])
        self.assertEqual(p2['planned'][len(p1['planned'])],{'role':'assistant','content':'a1'});self.assertEqual(p2['planned'][-1]['content'],'q2')
        self.assertEqual(p2['plan']['cache']['est_reused_chars_planned'],p1['plan']['cache']['est_prompt_chars_planned'])
        p3=self.c.plan(self.ev('q3'),'C3_LANGUAGE','OTHER SYS',vol(3),hist,'q3')  # pinned prefix changed -> rebuild
        self.assertEqual(p3['plan']['layout'],'stable_prefix');self.assertNotIn('append_reentry',p3['plan']['decisions'])
    def test_active_mode_requires_explicit_human(self):
        with self.assertRaises(PermissionError):self.c.set_mode('ACTIVE')
        self.c.set_mode('ACTIVE','EXPLICIT_HUMAN');hist=rows(*[('Q%d. '%i+LONG,'A%d. '%i+LONG) for i in range(10)])
        # This test checks operator authority, not an impossible exact-pin budget.
        self.c.cfg=dict(self.r.cfg,context_tokens=8192,answer_tokens=256)
        out=self.plan('hi',hist);self.assertTrue(out['applied']);self.assertEqual(out['messages'],out['planned']);self.assertNotEqual(out['planned'],out['legacy'])

class KnobAndLearningTests(Base):
    def test_risky_knob_raise_needs_stable_exact_recall(self):
        with self.assertRaises(ValueError):self.c.set_knob('cache_compression_aggressiveness',.6)
        self.c.set_knob('cache_compression_aggressiveness',.2)  # lowering is always allowed
        with self.assertRaises(ValueError):self.c.set_knob('exact_recent_pin',.5)
        for i in range(C.RECALL_MIN_PLANS):self.plan('q%d'%i,rows(('a','b')))
        self.assertTrue(self.c.report()['exact_span_recall']['stable']);self.assertEqual(self.c.set_knob('cache_compression_aggressiveness',.6),{'cache_compression_aggressiveness':.6})
        with self.assertRaises(ValueError):self.c.set_knob('nope',.1)
    def test_plan_touches_eligibility_and_outcome_updates_prior_shadow(self):
        hist=rows(*[('Q%d. '%i+LONG,'A%d. '%i+LONG) for i in range(10)])
        e=self.ev('q');self.c.plan(e,'C3_LANGUAGE','SYS',[],hist,'q')
        traces=self.r.store.rows("SELECT payload FROM packets WHERE kind='LearningTrace' AND event_id=?",(e,))
        self.assertTrue(any(json.loads(t['payload'])['path_id']==C.PATH for t in traces))
        self.assertEqual(N.kind_of(C.PATH),'control');self.assertEqual(N.kind_of('attention_policy'),'control')
        for _ in range(3):self.c.outcome(e,0.)
        st=self.c.report();self.assertLess(st['policy']['compress']['mean'],.5)
        self.assertEqual(self.c._shift(self.c._load()[0],'compress'),0.)  # learned prior stays SHADOW
        self.c.set_mode('ACTIVE','EXPLICIT_HUMAN','learned');self.assertLess(self.c._shift(self.c._load()[0],'compress'),0.)
    def test_observe_records_cache_reuse_and_cost_signal_only_when_applied(self):
        e=self.ev('q');self.c.plan(e,'C3_LANGUAGE','SYS',[],[],'q')
        out=self.c.observe(e,'C3_LANGUAGE',{'timings':{'cache_n':30,'prompt_n':10}})
        self.assertAlmostEqual(out['reuse_ratio'],.75);self.assertAlmostEqual(self.c.report()['measured_cache_reuse'],.75)
        self.assertEqual(self.r.store.rows("SELECT * FROM packets WHERE kind='ModulatorPacket' AND event_id=?",(e,)),[])
        self.c.set_mode('ACTIVE','EXPLICIT_HUMAN');e=self.ev('q2');self.c.plan(e,'C3_LANGUAGE','SYS',[],[],'q2');self.c.observe(e,'C3_LANGUAGE',{'timings':{'cache_n':0,'prompt_n':10}})
        self.assertEqual(len(self.r.store.rows("SELECT * FROM packets WHERE kind='ModulatorPacket' AND event_id=?",(e,))),1)


    def _invalid_cache_metric(self,cached,prompt):
        self.c.set_mode('ACTIVE','EXPLICIT_HUMAN')
        e=self.ev('invalid cache counters')
        self.c.plan(e,'C3_LANGUAGE','SYS',[],[],'invalid cache counters')
        out=self.c.observe(e,'C3_LANGUAGE',{'timings':{'cache_n':cached,'prompt_n':prompt}})
        self.assertIsNone(out['reuse_ratio'])
        self.assertIsNone(self.c.report()['measured_cache_reuse'])
        self.assertEqual(self.r.store.rows("SELECT * FROM packets WHERE kind='ModulatorPacket' AND event_id=?",(e,)),[])

    def test_negative_cached_tokens_cannot_drive_cost_learning(self):
        self._invalid_cache_metric(-5,10)

    def test_negative_prompt_tokens_cannot_drive_cost_learning(self):
        self._invalid_cache_metric(5,-1)

    def test_boolean_cached_tokens_cannot_drive_cost_learning(self):
        self._invalid_cache_metric(True,9)

    def test_valid_cache_counters_still_measure_cost(self):
        self.c.set_mode('ACTIVE','EXPLICIT_HUMAN')
        e=self.ev('valid cache counters')
        self.c.plan(e,'C3_LANGUAGE','SYS',[],[],'valid cache counters')
        out=self.c.observe(e,'C3_LANGUAGE',{'timings':{'cache_n':3,'prompt_n':7}})
        self.assertAlmostEqual(out['reuse_ratio'],.3)
        self.assertAlmostEqual(self.c.report()['measured_cache_reuse'],.3)

class WarmTests(Base):
    def remember(self,key,value):
        e=self.r.store.event(self.r.session,key)
        self.r.memory.feedback(e['event_id'],'fact',value,key=key)
        return self.r.store.one('SELECT id FROM memories ORDER BY id DESC LIMIT 1')['id']
    def test_warm_memory_reactivates_and_decays(self):
        mid=self.remember('favourite colour of the bike','blue')
        self.c.observe(self.ev('x'),'C3_LANGUAGE',{},memory_ids=[mid])
        w=self.c.warm('what colour is my bike',self.r.session,[])
        self.assertEqual(w['ids'],[mid]);self.assertFalse(w['applied']);self.assertEqual(w['items'][0]['value'],'blue')
        self.assertEqual(self.c.warm('completely unrelated',self.r.session,[])['ids'],[])
        for i in range(6):self.ev('later %d'%i)
        self.assertEqual(self.c.warm('what colour is my bike',self.r.session,[])['ids'],[])  # decayed below WARM_MIN
    def test_forgotten_memory_is_not_reactivated(self):
        mid=self.remember('door code','7')
        self.c.observe(self.ev('x'),'C3_LANGUAGE',{},memory_ids=[mid]);self.r.memory.forget(mid)
        self.assertEqual(self.c.warm('door code please',self.r.session,[])['ids'],[])

class RuntimeHookTests(Base):
    def install(self):
        self.native=[]
        def generate(messages,*a,**k):
            self.native.append(messages);yield 'ok answer'
        self.r._route=Mock(return_value=('simple',{'source':'TEST_ROUTE_SEAM'}))
        self.r.pool.get=Mock(return_value=SimpleNamespace(role='C3_LANGUAGE',last_metrics={'timings':{'cache_n':5,'prompt_n':5}},generate=generate))
        self.r.learner.output_delta=Mock(return_value=None)
    def wait(self):
        until=time.monotonic()+10
        while not self.r.idle() and time.monotonic()<until:time.sleep(.005)
        return self.r.last_answer()
    def test_turn_writes_context_plan_and_shadow_keeps_legacy_view(self):
        self.install();self.r.submit('hello there');row=self.wait();self.assertEqual(row['status'],'FINAL')
        meta=json.loads(row['metadata']);self.assertFalse(meta['context_plan']['applied'])
        p=json.loads(self.r.store.one("SELECT payload FROM packets WHERE kind='ContextPlan' ORDER BY created DESC LIMIT 1")['payload'])
        self.assertEqual(p['packet_id'],meta['context_plan']['packet_id']);self.assertEqual(self.native[-1][0]['role'],'system')
        self.assertEqual(self.c.report()['measured_cache_reuse'],.5)
        op=Operator(self.r);self.assertIn('SHADOW',op.run(':ctxos'));self.assertIn('ContextPlan'.lower()[:0]+'layout',op.run(':ctxos last'))
        self.assertIn('ACTIVE',op.run(':ctxos active'))
        self.r.submit('and again');self.assertEqual(self.wait()['status'],'FINAL')
        self.assertTrue(json.loads(self.r.last_answer()['metadata'])['context_plan']['applied'])

if __name__=='__main__':unittest.main()
