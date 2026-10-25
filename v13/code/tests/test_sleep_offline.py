"""WP-S7: sleep with offline compute (day digest, predictor consolidation, TTT candidates)."""
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from v13.runtime import Runtime
from v13.operator import Operator
from v13.sleep import SleepCycle
from v13 import sleep_offline as S
from v13 import fastforward as F
from v13.inputs import set_pause

class Base(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.r=Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled','off');self.r.sleep.cycle.set_policy('tick_seconds','300')
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def cycle(self):return SleepCycle(self.r.store,self.r.cfg,self.r.memory,self.r.consolidation,None,self.home)
    def turn(self,text,answer):
        def gen(messages,*a,**k):yield answer
        self.r._route=Mock(return_value=('simple',{'source':'TEST_ROUTE_SEAM'}))
        self.r.pool.get=Mock(return_value=SimpleNamespace(role='C3_LANGUAGE',last_metrics={},generate=gen));self.r.learner.output_delta=Mock(return_value=None)
        self.r.submit(text);until=time.monotonic()+10
        while not self.r.idle() and time.monotonic()<until:time.sleep(.005)

class DigestTests(Base):
    def test_digest_is_extractive_incremental_and_pins_exact_spans(self):
        self.turn('Remember: invoice 4711 is due on 2026-11-02. What should I do first? Please explain in detail with all steps.','First pay invoice 4711 before 2026-11-02. Then archive the receipt and note it in the ledger for the tax office.')
        self.turn('Thanks, and what about the second one?','The second one can wait until next week.')
        out=S.digest(self.r.store);self.assertEqual((out['sessions'],out['turns']),(1,2))
        v=S.view(self.r.store,self.r.session);self.assertEqual(v['fact_authority'],0)
        self.assertIn('4711',v['text']);self.assertIn('2026-11-02',v['text'])
        self.assertEqual(S.digest(self.r.store)['turns'],0)  # nothing new
        self.turn('One more question?','Sure.');self.assertEqual(S.digest(self.r.store)['turns'],1)
        self.assertIn('entries',json.loads(Operator(self.r).run(':sleep digest')))

class LiveContextTests(Base):
    def test_digest_reaches_live_context_only_outside_history_and_respects_deletion(self):
        self.r.cfg['history_turns']=2;seen=[]
        for i,fact in enumerate(['My locker code is 4471.','The wifi password is blue-otter-77.','Breakfast idea?','Boil an egg?']):self.turn(fact,'Noted %d.'%i)
        S.digest(self.r.store)
        def gen(messages,*a,**k):seen.append(messages[0]['content']);yield 'ok'
        self.r.pool.get=Mock(return_value=SimpleNamespace(role='C3_LANGUAGE',last_metrics={},generate=gen))
        def ask(q):
            self.r.submit(q);until=time.monotonic()+10
            while not self.r.idle() and time.monotonic()<until:time.sleep(.005)
            return [x for x in seen if 'internal' not in x[:40]][-1]
        sys=ask('What is my locker code?')
        self.assertIn('4471',sys);self.assertIn('blue-otter-77',sys);self.assertNotIn('Boil an egg',sys.split('compressed digest')[-1].split('Task context')[0])
        self.assertEqual(json.loads(self.r.last_answer()['metadata'])['digest_lines'],2)
        ev=self.r.store.one("SELECT source_id FROM events WHERE id=(SELECT event_id FROM messages WHERE text='My locker code is 4471.')")
        with self.r.store.tx() as c:c.execute('UPDATE sources SET deleted=1 WHERE id=?',(ev['source_id'],))
        self.assertNotIn('4471',ask('And the wifi?'))
        Operator(self.r).run(':ctxos digest off');self.assertNotIn('blue-otter-77',ask('Anything else?'))

class PredictorTests(Base):
    def test_consolidation_keeps_only_if_heldout_error_does_not_rise(self):
        f=F.FastForward(self.r.store);self.assertEqual(f.consolidate()['status'],'SKIPPED_TOO_FEW')
        for i in range(40):f.learn('e-%d'%i,F.features('q %d'%i,'simple','both' if i%2 else 'none'),20. if i%2 else 2.,'FINAL',100)
        rep=f.consolidate();self.assertIn(rep['status'],('KEPT','REVERTED'))
        if rep['status']=='KEPT':self.assertLessEqual(rep['heldout_error_after'],rep['heldout_error_before'])
        self.assertLessEqual(len(f._load()[0]['replay']),F.REPLAY_MAX)
    def test_exact_outcome_replay_is_idempotent_but_conflicting_replay_is_rejected(self):
        f=F.FastForward(self.r.store);x=F.features('one event','simple','none')
        first=f.learn('receipt-1',x,2.,'FINAL',100)
        self.assertEqual(f.learn('receipt-1',x,2.,'FINAL',100),first)
        self.assertEqual(f._load()[0]['n'],1)
        with self.assertRaisesRegex(ValueError,'Conflicting Fast-Forward outcome replay'):
            f.learn('receipt-1',x,3.,'FINAL',100)
        self.assertEqual(f._load()[0]['n'],1)

class PhaseTests(Base):
    def test_full_sleep_runs_offline_phase_and_stages_ttt_only(self):
        for i in range(3):self.turn('Question number %d about the garden?'%i,'Answer %d: water the roses.'%i)
        w=dict(F.FastForward(self.r.store)._load()[0]['w'])
        rep=self.cycle().run('a',origin='USER');ph=next(p for p in rep['phases'] if p['phase']=='SLEEP_A_OFFLINE')
        self.assertEqual(ph['status'],'DONE');self.assertFalse(ph['weight_updates']);self.assertEqual(ph['digest']['turns'],3)
        rows=[json.loads(x) for x in (self.home/'exports/sleep-ttt-candidates.jsonl').read_text().splitlines()]
        self.assertEqual(len(rows),2);self.assertTrue(all(x['status']=='CANDIDATE_NOT_TRAINED' for x in rows));self.assertIn('U: ',rows[0]['context'])
        set_pause(self.r.store,'training');self.turn('Another?','Yes.')
        ph=next(p for p in self.cycle().run('a',origin='USER')['phases'] if p['phase']=='SLEEP_A_OFFLINE');self.assertEqual(ph['ttt']['status'],'SKIPPED_PAUSED_TRAINING')
    def test_cancel_and_yellow(self):
        self.turn('Hi there?','Hello.');cy=self.cycle();cancel=threading.Event();cancel.set()
        rep=cy.run('a',cancel=cancel,origin='USER');self.assertNotIn('SLEEP_A_OFFLINE',[p['phase'] for p in rep['phases'] if p['status']=='DONE'])
        rep=cy.run('full',resource=lambda:'PRESSURE');self.assertEqual([p['phase'] for p in rep['phases']],['SLEEP_C'])

if __name__=='__main__':unittest.main()
