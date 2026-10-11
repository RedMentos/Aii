"""WP-T11: dream hypotheses are checked against stored sources; Sleep C measures control-parameter drift with a gate."""
import json
from pathlib import Path
import tempfile
import time
import unittest
from v13.runtime import Runtime
from v13.sleep import SleepCycle,DAY
from v13 import homeostasis as H
from v13 import authority as AU

class Clock:
    def __init__(self,t=None):self.t=t or time.time()
    def __call__(self):return self.t

class Base(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.r=Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled','off');self.r.sleep.cycle.set_policy('tick_seconds','300')
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def correction(self,question,value,kind='fact'):
        e=self.r.store.event(self.r.session,question);return self.r.memory.feedback(e['event_id'],kind,value)
    def verdicts(self,rid):
        return [json.loads(x['payload'])['outcome'] for x in self.r.store.rows("SELECT payload FROM packets WHERE kind='ReplayItem' AND json_extract(payload,'$.stage')='SLEEP_B_VALIDATION' AND json_extract(payload,'$.replay_id')=? ORDER BY rowid",(rid,))]

class HypothesisValidation(Base):
    def test_route_alternative_becomes_supported_by_later_human_route(self):
        self.correction('Erkläre Projekt Aurora genau','detail','route');c=Clock()
        cy=SleepCycle(self.r.store,self.r.cfg,self.r.memory,self.r.consolidation,None,self.home,c)
        b=cy.run('b',origin='USER')['phases'][0];h=b['hypotheses'][0]
        self.assertEqual(b['validation']['by_verdict'],{'UNVERIFIED':1});self.assertEqual(self.verdicts(h['replay_id']),['UNVERIFIED'])
        alt=json.loads(self.r.store.one("SELECT payload FROM packets WHERE kind='ReplayItem' AND json_extract(payload,'$.replay_id')=? AND json_extract(payload,'$.stage')='QUEUED'",(h['replay_id'],))['payload'])['hypothesis']['alternative_route']
        self.correction('Erkläre Projekt Aurora genau bitte',alt,'route')
        st,v=cy.queue.load();self.assertEqual(cy.validate_hypotheses(st,cy.policy(),limit=8)['checked'],0)  # not re-checked within a day
        c.t+=DAY+1;st,v=cy.queue.load();before=self.r.store.rows('SELECT * FROM memories')
        out=cy.validate_hypotheses(st,cy.policy(),limit=8);cy.queue.save(st,v)
        self.assertEqual(self.verdicts(h['replay_id'])[-1],'SUPPORTED');self.assertGreaterEqual(out['by_verdict'].get('SUPPORTED',0),1)
        self.assertEqual(before,self.r.store.rows('SELECT * FROM memories'))  # validation never writes facts
        p=json.loads(self.r.store.rows("SELECT payload FROM packets WHERE kind='ReplayItem' AND json_extract(payload,'$.stage')='SLEEP_B_VALIDATION' ORDER BY rowid DESC LIMIT 1")[0]['payload'])
        self.assertEqual((p['fact_write_authority'],p['max_authority']),(0,'HYPOTHESIS_NO_LEARNING'))
    def test_world_relation_retires_when_a_fact_is_superseded(self):
        self.correction('Projekt Aurora Budget?','120 Euro');self.correction('Projekt Borealis Budget?','120 Euro');c=Clock()
        cy=SleepCycle(self.r.store,self.r.cfg,self.r.memory,self.r.consolidation,None,self.home,c)
        st,v=cy.queue.load();cy.queue.sync(st,cy.policy());b=cy.sleep_b(st,cy.policy(),limit=8);cy.queue.save(st,v)
        h=next(x for x in b['hypotheses'] if x['kind']=='WORLD_RELATION');self.assertEqual(self.verdicts(h['replay_id']),['UNVERIFIED'])
        self.correction('Projekt Aurora Budget?','90 Euro')  # human correction supersedes the old fact
        c.t+=DAY+1;st,v=cy.queue.load();cy.queue.sync(st,cy.policy());cy.validate_hypotheses(st,cy.policy(),limit=16);cy.queue.save(st,v)
        self.assertEqual(self.verdicts(h['replay_id'])[-1],'STALE')
        self.assertEqual(cy.queue.load()[0]['items'][h['replay_id']]['retired'],'HYPOTHESIS_STALE')

class Homeostasis(Base):
    def test_gate_measures_saturation_and_drift_and_holds_slow_consolidation(self):
        first=H.run(self.r);self.assertEqual(first['gate']['status'],'PASS');self.assertIsNone(first['components']['attention_gains']['drift'])
        self.assertEqual(first['native_body_weights'],'UNAVAILABLE');self.assertFalse(H.holding(self.r.store))
        from v13.attention import controller,GAIN_MAX
        a=controller(self.r)
        def sat(st):st['gains']={k:GAIN_MAX for k in st['gains']}
        a._mutate(sat)
        from v13.jefbridge import controller as jc
        def jump(st):st['w']=[3.]*len(st['w'])
        jc(self.r)._mutate(jump)
        rep=H.run(self.r);g=rep['gate']
        self.assertEqual(g['status'],'FAIL');self.assertIn('attention_gains:saturation',g['failures']);self.assertIn('jef_bridge:drift',g['failures'])
        self.assertEqual(rep['components']['attention_gains']['saturation'],1.);self.assertTrue(H.holding(self.r.store))
        self.r.cfg['learning_mode']='SHADOW_UPDATE'
        self.assertEqual(AU.job(self.r,'learn_slow')['consolidate_held'],'HOMEOSTASIS_GATE_FAIL')
        def relax(st):st['gains']={k:.5 for k in st['gains']}
        a._mutate(relax);self.assertEqual(H.run(self.r)['gate']['status'],'PASS');self.assertFalse(H.holding(self.r.store))
    def test_sleep_c_runs_the_gate(self):
        c=self.r.sleep.cycle.run('c',origin='USER')['phases'][0]
        self.assertEqual(c['homeostasis_gate']['status'],'PASS');self.assertEqual(H.report(self.r.store)['last_gate']['status'],'PASS')

if __name__=='__main__':unittest.main()
