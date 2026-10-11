"""Controlled-clock software regressions, never native or phone proof."""
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from v13.common import Cancelled,Limits
from v13.contracts import offer_is_fresh
from v13.runtime import Runtime
from v13.runners import check
import integration_step2_utility as collector


class Clock:
    def __init__(self):self.now=100.
    def seconds(self):return self.now
    def nanoseconds(self):return int(self.now*1e9)


class SoftwareRunner:
    """Explicit synthetic JSON for testing budget propagation only."""
    def __init__(self,clock,durations):
        self.clock=clock;self.durations=iter(durations);self.calls=[];self.last_metrics={}
    def generate(self,messages,cancel,deadline,*args,**kwargs):
        self.calls.append(deadline);check(cancel,deadline)
        self.clock.now+=next(self.durations);check(cancel,deadline)
        self.last_metrics={'status':'SOFTWARE_FIXTURE'}
        yield json.dumps({'summary':'software fixture hypothesis','quotes':[],
                         'uncertainty':'software fixture','needs_reentry':False})


class OfferDeadlines(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name)
        self.r=Runtime(self.home);self.e=self.r.store.event(self.r.session,'Software fixture project budget.')
        self.clock=Clock()
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def clocked(self,runner):
        from contextlib import ExitStack
        stack=ExitStack()
        stack.enter_context(patch.object(time,'monotonic',self.clock.seconds))
        stack.enter_context(patch.object(time,'monotonic_ns',self.clock.nanoseconds))
        stack.enter_context(patch.object(self.r.pool,'get',return_value=runner))
        return stack
    def test_sequential_compute_budgets_do_not_expire_completed_turn_offers(self):
        runner=SoftwareRunner(self.clock,[22.,17.])
        with self.clocked(runner):
            a=self.r.cognition.offer('B1_DETAIL',self.e,0,135.,valid_until=190.)
            b=self.r.cognition.offer('B2_GIST',self.e,0,157.,valid_until=190.)
            self.assertEqual(runner.calls,[135.,157.])
            self.assertEqual(self.clock.now,139.)
            self.assertEqual(len(self.r.cognition.focal([a,b],self.e,0)),2)
            self.assertLess(a['compute_deadline_monotonic_ns'],time.monotonic_ns())
            self.assertEqual(a['deadline_monotonic_ns'],190_000_000_000)
            query=json.loads(self.r.store.one('SELECT payload FROM packets WHERE id=?',(a['query_packet_id'],))['payload'])
            self.assertEqual(query['compute_deadline_monotonic_ns'],135_000_000_000)
            self.assertEqual(query['offer_valid_until_monotonic_ns'],190_000_000_000)
            self.clock.now=191.
            self.assertEqual(self.r.cognition.focal([a,b],self.e,0),[])
    def test_default_background_expiry_stays_at_compute_deadline(self):
        runner=SoftwareRunner(self.clock,[22.,17.])
        with self.clocked(runner):
            a=self.r.cognition.offer('B1_DETAIL',self.e,0,135.)
            b=self.r.cognition.offer('B2_GIST',self.e,0,157.)
            self.assertEqual(a['deadline_monotonic_ns'],135_000_000_000)
            self.assertEqual(self.r.cognition.focal([a,b],self.e,0),[b])
    def test_expired_turn_prevents_reentry_before_query_or_model(self):
        runner=SoftwareRunner(self.clock,[1.]);self.clock.now=191.
        with self.clocked(runner),self.assertRaises(Limits):
            self.r.cognition.offer('B1_DETAIL',self.e,0,220.,valid_until=190.)
        self.assertEqual(runner.calls,[])
        self.assertEqual(self.r.store.rows("SELECT id FROM packets WHERE kind='QueryPacket'"),[])
    def test_validity_never_extends_inference_and_shorter_consumer_clamps_it(self):
        runner=SoftwareRunner(self.clock,[36.])
        with self.clocked(runner),self.assertRaises(Limits):
            self.r.cognition.offer('B1_DETAIL',self.e,0,135.,valid_until=190.)
        self.assertEqual(runner.calls,[135.])
        self.assertEqual(self.r.store.rows("SELECT id FROM packets WHERE kind='OfferPacket'"),[])
        self.clock.now=100.;runner=SoftwareRunner(self.clock,[11.])
        with self.clocked(runner),self.assertRaises(Limits):
            self.r.cognition.offer('B1_DETAIL',self.e,0,135.,valid_until=110.)
        self.assertEqual(runner.calls,[110.])
    def test_invalid_deadlines_never_create_query_or_call_model(self):
        runner=SoftwareRunner(self.clock,[])
        with self.clocked(runner):
            for value in (float('nan'),float('inf'),float('-inf'),0.,-1.,True,'190'):
                for kwargs in ({'deadline':value,'valid_until':190.},{'deadline':135.,'valid_until':value}):
                    with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):
                        self.r.cognition.offer('B1_DETAIL',self.e,0,**kwargs)
        self.assertEqual(runner.calls,[])
        self.assertEqual(self.r.store.rows("SELECT id FROM packets WHERE kind='QueryPacket'"),[])
    def test_generation_state_event_and_commit_checks_remain_strict(self):
        runner=SoftwareRunner(self.clock,[1.])
        with self.clocked(runner):
            a=self.r.cognition.offer('B1_DETAIL',self.e,0,135.,valid_until=190.)
            eid=self.e['event_id'];generation=self.e['brain_generation_id']
            for event,gen,version,committed in ((eid,'other',0,False),(eid,generation,1,False),('other',generation,0,False),(eid,generation,0,True)):
                self.assertFalse(offer_is_fresh(a,event,gen,version,committed))
    def test_cancelled_turn_never_creates_offer(self):
        runner=SoftwareRunner(self.clock,[1.]);self.r.cancel_event.set()
        with self.clocked(runner),self.assertRaises(Cancelled):
            self.r.cognition.offer('B1_DETAIL',self.e,0,135.,valid_until=190.)
        self.assertEqual(runner.calls,[])
        self.r.cancel_event.clear()
    def test_step2_consumer_uses_remaining_same_total_turn_budget(self):
        runner=SoftwareRunner(self.clock,[22.,17.,1.]);fixture=collector.FIXTURES[0]
        base={'state_before_restart':collector.states(self.r)}
        cfg=dict(self.r.cfg);variant=collector.VARIANTS[2]
        with self.clocked(runner),patch.object(collector,'Runtime',return_value=self.r),patch.object(self.r,'close'):
            row=collector.run_variant(self.home,fixture,variant,base,cfg)
        self.assertEqual(runner.calls,[135.,157.,190.])
        self.assertEqual(row['turn_deadline_monotonic_ns'],190_000_000_000)
        self.assertTrue(row['checks']['expected_offer_count'])
        # Synthetic runners cannot pass native/reap gates or constitute a proof.
        self.assertEqual(row['status'],'STRUCTURAL_FAIL')
        self.assertFalse(row['processes_reaped'])
    def test_installed_chat_lock_refuses_native_collector_before_any_work(self):
        with patch.object(collector,'run') as run:
            with self.assertRaises(BlockingIOError):
                collector.run_locked(self.home,self.home/'not-created.json')
            run.assert_not_called()
        self.assertFalse((self.home/'not-created.json').exists())
    def test_installed_collector_lock_released_on_failure(self):
        import fcntl
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp);(home/'data').mkdir()
            with patch.object(collector,'run',side_effect=RuntimeError('explicit software failure')):
                with self.assertRaisesRegex(RuntimeError,'explicit software failure'):
                    collector.run_locked(home,home/'unused.json')
            with open(home/'data/coordinator.lock','a+') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)


if __name__=='__main__':unittest.main()
