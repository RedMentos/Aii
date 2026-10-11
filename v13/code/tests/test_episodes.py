"""WP-N8 event segmentation, causal memory graph, admission/forgetting. No model needed."""
from pathlib import Path
import tempfile
import unittest
from v13.common import now
from v13.episodes import Episodes,observe_turn,controller,operator_command,noisy_or,GAINS
from v13.runtime import Runtime

class EpisodeBase(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.ep=controller(self.r);self.t=now()
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def turn(self,text,dt=5,**kw):
        self.t+=dt;e=self.r.store.event(self.r.session,text)
        return e,self.ep.observe(e['event_id'],self.r.session,text,clock=self.t,**kw)

class Segmentation(EpisodeBase):
    def test_same_topic_stays_and_topic_plus_route_change_cuts(self):
        _,a=self.turn('Plan the budget for Project Aurora',route='detail');self.assertTrue(a['cut']);self.assertEqual(a['reason'],'first')
        _,b=self.turn('Budget for Project Aurora: add travel costs',route='detail');self.assertFalse(b['cut']);self.assertEqual(b['episode_id'],a['episode_id'])
        _,c=self.turn('Write a poem about autumn leaves',route='simple');self.assertTrue(c['cut'])
        self.assertGreater(c['signals']['context_shift'],.9);self.assertEqual(c['signals']['action_transition'],1.)
        closed=self.ep.episodes(self.r.session);self.assertEqual(len(closed),1);self.assertEqual(len(closed[0]['events']),2)
        self.assertEqual(self.ep.relation(closed[0]['events'][0],closed[0]['events'][1])['relation'],'TEMPORAL')
    def test_surprise_alone_never_cuts(self):
        self.turn('Budget for Project Aurora');_,b=self.turn('Budget for Project Aurora',prediction_error=1.)
        self.assertFalse(b['cut']);self.assertAlmostEqual(noisy_or({'prediction_error':1.},GAINS),.25)
    def test_pause_correction_failure_and_max_events(self):
        self.turn('Budget Aurora');_,b=self.turn('Budget Aurora',dt=4000);self.assertTrue(b['cut']);self.assertEqual(b['signals']['pause'],1.)
        e,_=self.turn('Budget Aurora details');mid=self.r.memory.feedback(e['event_id'],'fact','120 Euro',key='Budget Aurora details')
        _,c=self.turn('Budget Aurora details again');self.assertTrue(c['cut']);self.assertEqual(c['signals']['correction'],1.)
        self.assertEqual(self.ep.relation(e['event_id'],mid)['relation'],'CAUSAL')
        self.r.cfg['episode_max_events']=2;self.turn('Budget Aurora x');_,d=self.turn('Budget Aurora x');self.assertTrue(d['cut']);self.assertEqual(d['reason'],'max_events')
    def test_goal_shift_and_semantic_vectors(self):
        v1=[1.]+[0.]*15;v2=[.98,.2]+[0.]*14;v3=[0.,1.]+[0.]*14
        self.turn('alpha',vector=v1);_,b=self.turn('beta',vector=v2);self.assertFalse(b['cut'])
        _,c=self.turn('gamma',vector=v3);self.assertTrue(c['cut']);self.assertEqual(c['signals']['context_shift'],1.)
        _,d=self.turn('gamma',vector=v3,task={'goal':'x'});self.assertTrue(d['cut']);self.assertEqual(d['signals']['goal_shift'],1.)

class Graph(EpisodeBase):
    def test_correlation_never_becomes_causation_by_counting(self):
        for _ in range(50):self.ep.link('mem_a','mem_b','CO_RETRIEVED')
        self.assertEqual(self.ep.relation('mem_b','mem_a')['relation'],'CORRELATIONAL')
        for _ in range(5):self.ep.hypothesize('evt_x','mem_a')
        self.assertEqual(self.ep.relation('evt_x','mem_a')['relation'],'HYPOTHESIS');self.assertEqual(self.ep.causes('mem_a'),[])
        self.ep.on_outcome('evt_x','act_1','FINAL');self.assertEqual(self.ep.effects('evt_x')[0]['b'],'outcome:act_1')
        with self.assertRaises(ValueError):self.ep.hypothesize('a','b','USER')
        with self.assertRaises(ValueError):self.ep.link('a','b','MAGIC')
    def test_recall_co_retrieval_spread_and_forget_cleanup(self):
        e,_=self.turn('Budget Aurora');m1=self.r.memory.feedback(e['event_id'],'fact','120',key='Budget Aurora')
        e,_=self.turn('Team Aurora');m2=self.r.memory.feedback(e['event_id'],'fact','Lena',key='Team Aurora')
        self.turn('Aurora overview',memory_ids=[m1,m2]);self.assertEqual(self.ep.related_memories([m1]),[m2])
        self.assertEqual(self.ep.relation(m1,m2)['relation'],'CORRELATIONAL');self.assertIsNotNone(self.ep.strength(m1))
        self.r.memory.forget(m1);self.assertEqual(self.ep.edges(m1),[]);self.assertIsNone(self.ep.strength(m1));self.assertTrue(self.ep.edges(m2))
        for k in ('mgraph','mstrength','episode'):
            for row in self.r.store.rows('SELECT payload FROM states WHERE key LIKE ?',(k+'%',)):self.assertNotIn('Aurora',row['payload'])

class Admission(EpisodeBase):
    def test_correction_episode_is_staging_candidate_plain_is_fast(self):
        self.turn('Budget Aurora');self.turn('Budget Aurora travel');ep=self.ep.close(self.r.session);self.assertEqual(ep['tier'],'FAST_EPISODIC')
        e,_=self.turn('Budget Aurora');self.r.memory.feedback(e['event_id'],'fact','120',key='Budget Aurora')
        ep=self.ep.close(self.r.session);self.assertEqual(ep['tier'],'SEMANTIC_STAGING_CANDIDATE');self.assertGreaterEqual(ep['admission'],.5)
    def test_strength_decays_and_forgetting_is_only_a_proposal(self):
        e,_=self.turn('Budget Aurora');mid=self.r.memory.feedback(e['event_id'],'fact','120',key='Budget Aurora')
        self.ep.reinforce([mid],self.t);s0=self.ep.strength(mid,self.t);self.assertAlmostEqual(self.ep.strength(mid,self.t+30*86400),s0/2)
        far=self.t+400*86400;props=self.ep.forgetting_candidates(self.r.session,clock=far);self.assertEqual([p['memory_id'] for p in props],[mid])
        self.assertEqual(self.r.store.one('SELECT active FROM memories WHERE id=?',(mid,))['active'],1)

class LiveHook(EpisodeBase):
    def test_full_sleep_closes_open_episodes(self):
        from v13.sleep import SleepCycle
        self.turn('Budget Aurora');rep=SleepCycle(self.r.store,self.r.cfg,self.r.memory).run('full')
        self.assertEqual(rep['episodes_closed'],1);self.assertIsNone(self.ep.current(self.r.session));self.assertEqual(self.ep.episodes(self.r.session)[0]['closed_by']['reason'],'sleep')
    def test_observe_turn_reads_turn_products_and_operator(self):
        e=self.r.store.event(self.r.session,'Plan Project Aurora')
        out=observe_turn(self.r,e,{'route':'detail','memory_ids':[]},'FINAL');self.assertTrue(out['cut'])
        e2=self.r.store.event(self.r.session,'Plan Project Aurora budget')
        out2=observe_turn(self.r,e2,{'route':'detail','memory_ids':[]},'ERROR');self.assertEqual(out2['episode_id'],out['episode_id'])
        st=operator_command(self.r,[]);self.assertEqual(len(st['open']['events']),2);self.assertEqual(st['edges']['TEMPORAL'],1)
        self.assertIsNotNone(operator_command(self.r,['cut']));self.assertEqual(len(operator_command(self.r,['list'])),1)
        with self.assertRaises(ValueError):operator_command(self.r,['bogus'])
        row=self.r.store.one("SELECT metrics FROM telemetry WHERE kind='episode_boundary' ORDER BY id DESC LIMIT 1");self.assertIn('score',row['metrics']);self.assertNotIn('Aurora',row['metrics'])

class Spread(EpisodeBase):
    """WP-N8 rest: associative spread in recall (SHADOW default), no self-reinforcement, consolidation priority."""
    def mems(self):
        e,_=self.turn('Project Aurora budget');a=self.r.memory.feedback(e['event_id'],'fact','120 Euro',key='Project Aurora budget')
        e,_=self.turn('Aurora team lead');b=self.r.memory.feedback(e['event_id'],'fact','Mira',key='Aurora team lead')
        return a,b
    def recalled(self,query):
        return self.r.memory.recall(query,self.r.session)
    def test_spread_needs_repeated_edges_shadow_reports_on_applies(self):
        a,b=self.mems();self.assertEqual(self.ep.spread_mode(),'shadow')
        base=self.recalled('What is the Project Aurora budget?');self.assertEqual([m['id'] for m in base],[a])
        self.ep.link(a,b,'CO_RETRIEVED')
        self.assertEqual(self.ep.spread('q',self.r.session,base)[1],[])  # one co-retrieval is chance
        self.ep.link(a,b,'CO_RETRIEVED')
        meta={};out=__import__('v13.episodes',fromlist=['x']).recall_turn(self.r,'q',base,meta)
        self.assertEqual([m['id'] for m in out],[a]);self.assertEqual(meta['associative_shadow'][0]['memory_id'],b);self.assertNotIn('associative_memory_ids',meta)
        self.ep.set_spread_mode('on');meta={};out=__import__('v13.episodes',fromlist=['x']).recall_turn(self.r,'q',base,meta)
        self.assertEqual([m['id'] for m in out],[a,b]);extra=out[1]
        self.assertEqual(extra['retrieval_channel'],'associative');self.assertAlmostEqual(extra['retrieval_score'],.6*base[0]['retrieval_score'],3)
        self.assertEqual(self.r.store.read_source(extra['source_ref']),'Mira');self.assertEqual(meta['associative_memory_ids'],[b])
        self.ep.set_spread_mode('off');self.assertEqual(self.ep.spread('q',self.r.session,base),(base,[]))
        with self.assertRaises(ValueError):self.ep.set_spread_mode('loud')
    def test_spread_added_memory_does_not_strengthen_its_own_edge(self):
        a,b=self.mems();key=lambda:[e for e in self.ep.edges(a) if e['kind']=='CO_RETRIEVED']
        self.ep.link(a,b,'CO_RETRIEVED');self.ep.link(a,b,'CO_RETRIEVED');n=key()[0]['count']
        self.turn('x',memory_ids=[a,b],associative_ids=[b]);self.assertEqual(key()[0]['count'],n)
        self.turn('y',memory_ids=[a,b]);self.assertEqual(key()[0]['count'],n+1)
    def test_forgotten_or_inactive_neighbour_is_skipped(self):
        a,b=self.mems();self.ep.link(a,b,'CO_RETRIEVED');self.ep.link(a,b,'CO_RETRIEVED');self.ep.set_spread_mode('on')
        with self.r.store.tx() as c:c.execute("UPDATE memories SET active=0 WHERE id=?",(b,))
        base=self.recalled('What is the Project Aurora budget?');self.assertEqual(self.ep.spread('q',self.r.session,base)[1],[])
    def test_live_turn_runs_spread_hook_and_operator(self):
        from v13.operator import Operator
        op=Operator(self.r);self.assertIn('shadow',op.run(':episodes spread'));self.assertIn('on',op.run(':episodes spread on'))
        self.r._turn(self.r.store.event(self.r.session,'Copy exactly: hello'))
        self.assertIsNone(self.r.store.one("SELECT id FROM telemetry WHERE kind='episodes_unavailable'"))
    def test_staging_events_lists_candidate_episodes_only(self):
        from v13.episodes import staging_events
        e,_=self.turn('Budget Aurora');self.r.memory.feedback(e['event_id'],'fact','120 Euro',key='Budget Aurora')
        ep=self.ep.close(self.r.session);self.assertEqual(ep['tier'],'SEMANTIC_STAGING_CANDIDATE');self.assertIn(e['event_id'],staging_events(self.r.store))
        f,_=self.turn('plain chat');self.ep.close(self.r.session);self.assertNotIn(f['event_id'],staging_events(self.r.store))

if __name__=='__main__':unittest.main()
