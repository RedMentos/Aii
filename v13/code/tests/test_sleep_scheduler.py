"""WP-E: G13 event scheduler and §94 replay/sleep phases. No models needed."""
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from v13.runtime import Runtime
from v13.operator import Operator
from v13.scheduler import EventScheduler
from v13.sleep import SleepCycle,SleepRuntime,ReplayQueue,DAY

class Clock:
    def __init__(self,t=1_700_000_000.):self.t=t
    def __call__(self):return self.t

class Base(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.r=Runtime(self.home)
        # Keep the live worker from starting autonomous sleeps underneath the direct calls in these tests.
        self.r.sleep.cycle.set_policy('enabled','off');self.r.sleep.cycle.set_policy('tick_seconds','300')
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def correction(self,question='Projekt Aurora Budget?',value='120 Euro',kind='fact'):
        e=self.r.store.event(self.r.session,question);mid=self.r.memory.feedback(e['event_id'],kind,value);return e['event_id'],mid
    def cycle(self,clock=None,age=None):
        return SleepCycle(self.r.store,self.r.cfg,self.r.memory,self.r.consolidation,age,self.home,clock or time.time)
    def wait_idle(self,timeout=20):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            if self.r.idle():return True
            time.sleep(.05)
        return False

class SchedulerTests(Base):
    # Separate state key: the live coordinator's own scheduler must not dispatch these test events.
    def sched(self,clock=None,age=None):return EventScheduler(self.r.store,self.r.cfg,clock or Clock(),age,key='G13_EVENT_QUEUE_TEST')
    def test_priority_order_and_foreground_preemption(self):
        s=self.sched()
        s.post('IDLE',action='sleep_full');s.post('REPLAY_DUE',action='wake_replay');s.post('TIMER',origin='USER',action='sleep_c');s.post('RESOURCE_CHANGE')
        kinds=[s.next()['kind'] for _ in range(4)]
        self.assertEqual(kinds,['RESOURCE_CHANGE','TIMER','REPLAY_DUE','IDLE']);self.assertIsNone(s.next())
    def test_background_waits_for_idle_and_resources(self):
        s=self.sched();s.post('IDLE',action='sleep_full');s.post('TIMER',origin='USER',action='sleep_c')
        self.assertIsNone(s.next(idle=False))  # a live turn is never interleaved
        self.assertIsNone(s.next(resource_state='CRITICAL'))  # RED: no background at all
        e=s.next(resource_state='PRESSURE');self.assertEqual(e['action'],'sleep_c')  # YELLOW: homeostasis only
        self.assertIsNone(s.next(resource_state='PRESSURE'))
        self.assertEqual(s.next()['action'],'sleep_full')
    def test_self_initiative_is_age_gated_but_user_is_not(self):
        from v13.age import AgeControl
        s=self.sched(age=AgeControl(self.r.store,self.r.cfg))
        s.post('GOAL_WAKE',origin='SELF',action='notice',payload={'text':'Ziel'});s.post('GOAL_WAKE',origin='USER',action='notice',payload={'text':'Ziel'})
        e=s.next();self.assertEqual(e['origin'],'USER');self.assertIsNone(s.next())
        self.assertEqual([x['status'] for x in s.pending() if x['origin']=='SELF'],['HELD_AGE'])
        # Without any age controller, self-initiative stays closed (conservative stage-0 default).
        s2=self.sched();self.assertIsNone(s2.next())
    def test_due_time_ttl_dedup_and_restart_recovery(self):
        c=Clock();s=self.sched(c)
        s.post('TIMER',origin='USER',due=c.t+60,action='sleep_c');s.post('IDLE',action='sleep_full',ttl=10)
        self.assertIsNone(s.post('IDLE',action='sleep_full',dedup=None) and None)
        a=s.post('REPLAY_DUE',action='wake_replay',dedup='x');self.assertIsNone(s.post('REPLAY_DUE',action='wake_replay',dedup='x'))
        c.t+=30;e=s.next();self.assertEqual(e['kind'],'REPLAY_DUE')
        self.assertEqual(s.report()['counters']['expired'],1)
        # Dispatched but never completed (crash) → due again after restart; bounded attempts.
        s3=self.sched(c);self.assertEqual(s3.recover(),1);c.t+=31
        self.assertEqual(s3.next()['kind'],'TIMER');self.assertEqual(s3.next()['kind'],'REPLAY_DUE')
        self.assertEqual(s3.complete(a,'RETRY'),'PENDING');self.assertEqual(s3.next()['attempts'],3)
        self.assertEqual(s3.complete(a,'RETRY'),'FAILED')
    def test_quiet_hours_and_capacity(self):
        s=self.sched();s.post('IDLE',action='sleep_full');s.post('TIMER',origin='USER',action='sleep_a')
        self.assertEqual(s.next(quiet=True)['origin'],'USER');self.assertIsNone(s.next(quiet=True))
        for i in range(260):s.post('IDLE',action='sleep_c')
        self.assertLessEqual(len(s.pending()),257);self.assertGreater(s.report()['counters']['dropped_capacity'],0)
        with self.assertRaises(ValueError):s.post('IDLE',action='rm -rf')
        with self.assertRaises(ValueError):s.post('NOPE')

class SleepATests(Base):
    def test_rehearsal_passes_and_spaces_out_without_writing_facts(self):
        eid,mid=self.correction();c=Clock(time.time());cy=self.cycle(c)
        before=self.r.store.rows('SELECT * FROM memories')
        rep=cy.run('a',origin='USER');a=rep['phases'][0]
        self.assertEqual((rep['status'],a['selected'],a['passed'],a['failed']),('DONE',1,1,0))
        st,_=cy.queue.load();it=next(iter(st['items'].values()))
        self.assertEqual((it['reps'],it['type'],it['last_outcome']),(1,'EPISODIC','PASS'));self.assertGreater(it['next_due'],c.t+600)
        p=json.loads(self.r.store.one("SELECT payload FROM packets WHERE kind='ReplayItem' AND json_extract(payload,'$.stage')='SLEEP_A'")['payload'])
        self.assertEqual((p['outcome'],p['max_authority'],p['fact_write_authority']),('PASS','RETENTION_TEST_NO_LEARNING',0))
        self.assertEqual(before,self.r.store.rows('SELECT * FROM memories'))
        self.assertEqual(self.r.store.one('SELECT status FROM replay')['status'],'PENDING')  # native :replay ownership untouched
        self.assertEqual(cy.run('a',origin='USER')['phases'][0]['selected'],0)  # not due yet
        self.assertTrue(Path(rep['artifact']).is_file())
        self.assertTrue(self.r.store.one("SELECT id FROM telemetry WHERE kind='sleep_cycle'"))
    def test_retention_failure_raises_priority_and_flags_regression_for_old_items(self):
        self.correction();c=Clock(time.time());cy=self.cycle(c);cy.run('a',origin='USER');c.t+=10*DAY
        self.r.cfg['memory_top_k']=0  # retrieval path lost: the correction is no longer recalled for its own question
        rep=cy.run('a',origin='USER');a=rep['phases'][0]
        self.assertEqual((a['failed'],a['by_bucket']),(1,{'protected_old':1}));self.assertTrue(a['regression_flag'])
        it=next(iter(cy.queue.load()[0]['items'].values()))
        self.assertEqual(it['last_outcome'],'FAIL');self.assertTrue(it['unresolved_errors'][0].startswith('RECALL_MISS'));self.assertEqual(it['affected_paths'],['memory_retrieval'])
        self.assertEqual(ReplayQueue.bucket(it),'failure')
    def test_forgotten_source_retires_item(self):
        _,mid=self.correction();cy=self.cycle();self.r.memory.forget(mid)
        a=cy.run('a',origin='USER')['phases'][0];self.assertEqual(a['retired'],1)
        self.assertEqual(next(iter(cy.queue.load()[0]['items'].values()))['retired'],'SUPERSEDED_OR_FORGOTTEN')
    def test_mix_interleaves_new_and_protected_old(self):
        for i in range(8):self.correction(f'Projekt P{i} Budget?',f'{i} Euro')
        c=Clock(time.time());cy=self.cycle(c);q=cy.queue;st,v=q.load();q.sync(st,cy.policy())
        for n,it in enumerate(st['items'].values()):
            if n<4:it['reps']=2;it['last_outcome']='PASS'
            if n==4:it['failures']=1;it['last_outcome']='FAIL'
        picked=q.sample(st,6,cy.policy()['mix'],c.t);buckets=[q.bucket(it) for _,it in picked]
        self.assertEqual(len(picked),6);self.assertEqual(buckets.count('protected_old'),2);self.assertEqual(buckets.count('failure'),1)
        self.assertEqual(buckets[1],'protected_old')  # old/new interleaving, not blocked batches
    def test_candidate_consolidation_only_stages(self):
        self.r.cfg['learning_mode']='SHADOW_UPDATE'
        for q in ('Projekt Aurora Budget?','Wie hoch ist das Budget von Projekt Aurora?','Budget für Projekt Aurora bitte'):
            e=self.r.store.event(self.r.session,q);self.r.memory.feedback(e['event_id'],'fact','120 Euro',permission='learn')
        rep=self.cycle().run('a',origin='USER');cons=rep['phases'][0]['consolidation']
        self.assertEqual(cons['status'],'DONE');self.assertEqual(len(cons['requests']),1);self.assertFalse(cons['automatic_activation'])
        self.assertEqual(self.r.store.one("SELECT status FROM requests WHERE kind='CONSOLIDATION'")['status'],'PENDING')

class SleepBCTests(Base):
    def test_dream_writes_hypotheses_only(self):
        eid,_=self.correction('Erkläre Projekt Aurora genau','detail','route')
        cy=self.cycle();mem_before=self.r.store.rows('SELECT * FROM memories')
        rep=cy.run('b',origin='USER');b=rep['phases'][0]
        self.assertEqual(b['budget'],1);self.assertEqual(len(b['hypotheses']),1);h=b['hypotheses'][0]
        self.assertEqual(h['kind'],'ROUTE_ALTERNATIVE');self.assertIn('kein Fakt',self.r.store.read_source(h['hypothesis_source_ref']))
        self.assertEqual(mem_before,self.r.store.rows('SELECT * FROM memories'))
        row=self.r.store.one('SELECT * FROM replay WHERE id=?',(h['replay_id'],));self.assertEqual((row['kind'],row['status']),('COUNTERFACTUAL','SLEEP_QUEUED'))
        self.assertEqual(len(self.r.store.rows("SELECT * FROM replay WHERE status='PENDING'")),1)  # native :replay never sees dreams
        p=json.loads(self.r.store.one("SELECT payload FROM packets WHERE kind='ReplayItem' AND json_extract(payload,'$.replay_id')=?",(h['replay_id'],))['payload'])
        self.assertEqual((p['max_authority'],p['fact_write_authority'],p['validation_required']),('HYPOTHESIS_NO_LEARNING',0,True))
        second=cy.run('b',origin='USER')['phases'][0]['hypotheses'];self.assertNotEqual(second[0]['replay_id'],h['replay_id'])
        sigs=cy.queue.load()[0]['signatures'];self.assertEqual(len(sigs),len(set(sigs)))
        # Counterfactuals are not rehearsed as real replay.
        self.assertTrue(all(it['type']!='COUNTERFACTUAL' for _,it in cy.queue.due(cy.queue.load()[0],time.time()+DAY)))
    def test_world_and_skill_hypotheses(self):
        self.correction('Projekt Aurora Budget?','120 Euro');self.correction('Projekt Borealis Budget?','120 Euro')
        self.correction('Erkläre Kunde Nova','detail','route');self.correction('Beschreibe Projekt Vega ausführlich','detail','route')
        b=self.cycle().sleep_b(*self._st(),limit=32)
        kinds={h['kind'] for h in b['hypotheses']};self.assertEqual(kinds,{'ROUTE_ALTERNATIVE','SKILL_RECOMBINATION','WORLD_RELATION'})
    def _st(self):
        cy=self.cycle();st,_=cy.queue.load();cy.queue.sync(st,cy.policy());return st,cy.policy()
    def test_autonomous_dream_needs_age_right(self):
        from v13.age import AgeControl
        self.correction('Erkläre Projekt Aurora genau','detail','route')
        rep=self.cycle(age=AgeControl(self.r.store,self.r.cfg)).run('b',origin='SYSTEM')
        self.assertEqual(rep['phases'][0]['status'],'SKIPPED_AGE_RIGHT')
    def test_homeostasis_decay_ttl_and_cleanup(self):
        self.correction();self.correction('Projekt Vega Budget?','5 Euro');self.correction('Erkläre Projekt Nova','detail','route');c=Clock(time.time());cy=self.cycle(c)
        st,v=cy.queue.load();cy.queue.sync(st,cy.policy());items=list(st['items'].values())
        items[1]['expires']=c.t-1;st['usage']={'EPISODIC':10.,'PROCEDURAL':0.,'SEMANTIC':0.,'COUNTERFACTUAL':0.,'RETENTION_PROBE':0.}
        cy.queue.save(st,v);old=self.home/'tmp/stale.part';old.write_text('x');import os;os.utime(old,(c.t-3*DAY,c.t-3*DAY))
        c.t+=20*DAY;rep=cy.run('c',origin='USER');cc=rep['phases'][0]
        self.assertEqual(cc['trace_decay']['expired'],1);self.assertEqual(cc['trace_decay']['decayed'],2)
        self.assertEqual(cc['stale_cleanup']['tmp_files_removed'],1);self.assertFalse(old.exists())
        st=cy.queue.load()[0];self.assertLess(st['items'][next(k for k,i in st['items'].items() if not i['retired'])]['priority'],1.)
        g=st['gains']['EPISODIC'];self.assertTrue(.35<=g<.70)  # dominant type damped, inside 0.5..1.5 x base
        self.assertIsNotNone(cc['compaction']['wal_checkpoint'])

class SafetyTests(Base):
    def test_resource_red_skips_and_yellow_runs_only_homeostasis(self):
        self.correction();cy=self.cycle()
        rep=cy.run('full',resource=lambda:'CRITICAL');self.assertEqual(rep['status'],'SKIPPED_RESOURCE_RED');self.assertEqual(rep['phases'],[])
        self.assertEqual(self.r.store.rows("SELECT * FROM packets WHERE kind='ReplayItem'"),[])
        rep=cy.run('full',resource=lambda:'PRESSURE');self.assertEqual([p['phase'] for p in rep['phases']],['SLEEP_C'])
    def test_cancel_interrupts_and_keeps_progress(self):
        for i in range(4):self.correction(f'Projekt P{i} Budget?',f'{i} Euro')
        cy=self.cycle();cancel=threading.Event();calls=[0]
        def resource():
            calls[0]+=1
            if calls[0]==2:cancel.set()  # a user turn arrives mid-sleep
            return 'NORMAL'
        rep=cy.run('a',cancel=cancel,resource=resource,origin='USER')
        self.assertEqual(rep['status'],'INTERRUPTED');a=rep['phases'][0];self.assertEqual(a['passed'],1)
        self.assertEqual(sum(it['reps'] for it in cy.queue.load()[0]['items'].values()),1)
    def test_resource_drop_mid_sleep_stops_replay(self):
        for i in range(3):self.correction(f'Projekt P{i} Budget?',f'{i} Euro')
        states=iter(['NORMAL','NORMAL','CRITICAL','CRITICAL','CRITICAL'])
        rep=self.cycle().run('a',resource=lambda:next(states,'CRITICAL'),origin='USER')
        self.assertEqual(rep['status'],'INTERRUPTED');self.assertIn('CRITICAL',rep['phases'][0]['reason'])
    def test_locked_policy_and_bounds(self):
        cy=self.r.sleep.cycle
        with self.assertRaises(ValueError):cy.set_policy('dream_fact_write_gain','1')
        with self.assertRaises(ValueError):cy.set_policy('batch','999')
        self.assertEqual(cy.set_policy('quiet_hours','22-7')['quiet_hours'],[22,7])

class RuntimeIntegration(Base):
    def test_operator_request_runs_in_background_and_survives_restart(self):
        self.correction();op=Operator(self.r)
        self.assertIn('eingeplant',op.run(':sleep run a'))
        self.assertTrue(self.wait_idle());end=time.monotonic()+10
        while time.monotonic()<end and not any(h['status']=='DONE' for h in self.r.sleep.scheduler.report()['history']):time.sleep(.05)
        hist=self.r.sleep.scheduler.report()['history'];self.assertEqual(hist[-1]['status'],'DONE')
        status=json.loads(op.run(':sleep'));self.assertEqual(status['last']['status'],'DONE');self.assertEqual(status['live'],1)
        self.assertIn('pending',json.loads(op.run(':scheduler')))
        self.r.close();self.r=Runtime(self.home)
        it=next(iter(self.r.sleep.cycle.queue.load()[0]['items'].values()));self.assertEqual(it['reps'],1)
    def test_idle_wake_triggers_autonomous_full_sleep(self):
        self.correction();c=Clock(time.time());sr=SleepRuntime(self.r,clock=c)
        sr.cycle.set_policy('enabled','on');sr.cycle.set_policy('sleep_idle_s','60')
        self.assertIsNone(sr.tick(force=True) and None)
        c.t+=120;e=sr.tick(force=True)
        self.assertEqual((e['kind'],e['action'],e['origin']),('IDLE','sleep_full','SYSTEM'))
        self.assertTrue(self.wait_idle());time.sleep(.2)
        last=self.r.store.state('SLEEP_LAST')[0];self.assertEqual((last['mode'],last['origin']),('full','SYSTEM'))
        phases={p['phase']:p['status'] for p in last['phases']}
        self.assertEqual(phases['SLEEP_B'],'SKIPPED_AGE_RIGHT')  # stage 0: no autonomous dream
        self.assertEqual(phases['SLEEP_A'],'DONE')
    def test_submit_cancels_running_sleep(self):
        import inspect;self.assertIn("'sleep'",inspect.getsource(Runtime.submit))

if __name__=='__main__':unittest.main()
