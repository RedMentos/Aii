"""§22.2.4 observer scheduling knob + §73 RSS budget as a resource-mode input (fixtures, no models)."""
import json
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from v13 import observer_schedule as obs
from v13 import resource_modes as rm
from v13 import effort
from v13.common import Cancelled
from v13.config import DEFAULTS,validate
from v13.operator import Operator
from v13.runtime import Runtime

BOTH=['B1_DETAIL','B2_GIST']
CFG={'minimum_free_mb':500,'thermal_limit_c':45.}
MB=1048576

class Plan(unittest.TestCase):
    def test_every_canon_schedule(self):
        self.assertEqual(obs.SCHEDULES,('A_THEN_B_SEQUENTIAL','B_THEN_A_SEQUENTIAL','ALWAYS_BOTH_ASYNC','JEF_FIRST_THEN_BOTH','SAMPLED_OBSERVER','ON_DEMAND_REENTRY'))
        p=lambda s,**k:obs.plan(s,['B2_GIST','B1_DETAIL'],'evt_1',**k)
        self.assertEqual(p('A_THEN_B_SEQUENTIAL')['pre'],BOTH);self.assertEqual(p('B_THEN_A_SEQUENTIAL')['pre'],BOTH[::-1])
        self.assertEqual((p('ALWAYS_BOTH_ASYNC')['parallel'],p('ALWAYS_BOTH_ASYNC')['reason']),(False,'ASYNC_NEEDS_TWO_RESIDENT_BODIES'))
        self.assertTrue(p('ALWAYS_BOTH_ASYNC',parallel_ok=True)['parallel'])
        self.assertFalse(obs.plan('ALWAYS_BOTH_ASYNC',['B1_DETAIL'],'e',parallel_ok=True)['parallel'])  # one body (e.g. ORANGE) is never parallel
        self.assertEqual((p('JEF_FIRST_THEN_BOTH')['pre'],p('JEF_FIRST_THEN_BOTH')['post']),([],BOTH))
        self.assertEqual((p('ON_DEMAND_REENTRY')['pre'],p('ON_DEMAND_REENTRY')['reentry']),([],True))
        self.assertEqual(p('SAMPLED_OBSERVER',rate=1.)['pre'],BOTH);self.assertEqual(p('SAMPLED_OBSERVER',rate=0.)['reason'],'SAMPLED_OUT')
        with self.assertRaises(ValueError):obs.plan('BOTH_PLEASE',BOTH,'e')

    def test_sampling_is_deterministic_and_near_the_rate(self):
        hits=[obs.sampled('evt_%d'%i,.3) for i in range(2000)]
        self.assertEqual(hits,[obs.sampled('evt_%d'%i,.3) for i in range(2000)]);self.assertTrue(.25<sum(hits)/2000<.35)

    def test_background_follows_the_schedule(self):
        self.assertEqual(obs.background('ON_DEMAND_REENTRY','e',.5,BOTH),[])
        self.assertEqual(obs.background('JEF_FIRST_THEN_BOTH','e',.5,BOTH,['B2_GIST']),['B2_GIST'])
        self.assertEqual(obs.background('SAMPLED_OBSERVER','e',0.,BOTH),[]);self.assertEqual(obs.background('A_THEN_B_SEQUENTIAL','e',0.,BOTH),BOTH)

class Run(unittest.TestCase):
    def test_sequential_keeps_peer_and_order(self):
        seen=[];out=obs.run(obs.plan('B_THEN_A_SEQUENTIAL',BOTH,'e'),lambda r,peer:seen.append((r,peer)) or r,time.monotonic()+60,Mock())
        self.assertEqual(out,BOTH[::-1]);self.assertEqual(seen,[('B2_GIST',True),('B1_DETAIL',True)])

    def test_parallel_really_overlaps_and_starts_without_peer(self):
        gate=threading.Barrier(2,timeout=5);seen=[]
        def ask(role,peer):gate.wait();seen.append(peer);return role  # both must be inside ask at once
        out=obs.run(obs.plan('ALWAYS_BOTH_ASYNC',BOTH,'e',parallel_ok=True),ask,time.monotonic()+60,Mock())
        self.assertEqual(out,BOTH);self.assertEqual(seen,[False,False])

    def test_errors_are_logged_and_cancel_propagates(self):
        err=Mock()
        def ask(role,peer):
            if role=='B1_DETAIL':raise ValueError('bad offer')
            return role
        self.assertEqual(obs.run(obs.plan('ALWAYS_BOTH_ASYNC',BOTH,'e',parallel_ok=True),ask,time.monotonic()+60,err),['B2_GIST'])
        self.assertEqual(err.call_args[0][0],'B1_DETAIL')
        def stop(role,peer):raise Cancelled('user')
        for parallel in (True,False):
            with self.assertRaises(Cancelled):obs.run(obs.plan('ALWAYS_BOTH_ASYNC',BOTH,'e',parallel_ok=parallel),stop,time.monotonic()+60,Mock(),cancelled=(Cancelled,))
        self.assertEqual(obs.run(obs.plan('A_THEN_B_SEQUENTIAL',BOTH,'e'),Mock(),time.monotonic()+.5,Mock()),[])  # no time left: no pass

class RssBudget(unittest.TestCase):
    def snap(self,mb=4000,procs=()):return {'mem_available_bytes':mb*MB,'battery_temperature_c':30.,'processes':list(procs)}
    def test_redmi_targets_only_on_android(self):
        self.assertIsNone(rm.boot_profile(CFG,{'android':False})['rss_mb'])
        p=rm.boot_profile(CFG,{'android':True});self.assertEqual(p['rss_mb'],{'YELLOW':3000.,'ORANGE':3800.});self.assertEqual(p['rss_status'],'BOOT_REDMI_TARGET')
        big=self.snap(procs=[{'rss_bytes':2500*MB,'pss_bytes':None},{'rss_bytes':900*MB,'pss_bytes':700*MB}])
        self.assertEqual(rm.total_rss_mb(big),3200.)  # PSS where measured, else RSS
        self.assertEqual(rm.classify(big,p),('YELLOW',['RSS_OVER_YELLOW']));self.assertEqual(rm.classify(big,rm.boot_profile(CFG,{'android':False}))[0],'GREEN')
        self.assertEqual(rm.classify(self.snap(procs=[{'rss_bytes':3900*MB}]),p)[0],'ORANGE')
        self.assertEqual(rm.classify(self.snap(procs=[{'rss_bytes':3700*MB}]),p,'ORANGE')[0],'ORANGE')  # hysteresis: under 3800 but not by 5 %
        self.assertEqual(rm.classify(self.snap(procs=[{'rss_bytes':3500*MB}]),p,'ORANGE')[0],'YELLOW')
        with self.assertRaises(ValueError):rm.validate(dict(p,rss_mb={'YELLOW':3900.,'ORANGE':3000.}))

class Knob(unittest.TestCase):
    def test_config_default_keeps_old_behaviour_and_rejects_unknown(self):
        self.assertEqual(DEFAULTS['observer_schedule'],'A_THEN_B_SEQUENTIAL');self.assertEqual(DEFAULTS['observer_sample_rate'],.5)
        with self.assertRaises(ValueError):validate(DEFAULTS|{'observer_schedule':'BOTH'})

OFFER={'packet_id':'pkt_x','offer':{'summary':'note','needs_reentry':False,'quotes':[]},'evidence_refs':[]}
class Turn(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.r.sleep.cycle.set_policy('enabled','off')
        op=Operator(self.r);op.run(':route both');effort.set_mode(self.r.store,'max')
        self.r.learner.output_delta=Mock(return_value=None);self.calls=[];self.lock=threading.Lock()
        def offer(role,e,version,deadline,peer=None,**kw):
            with self.lock:self.calls.append((role,self.r.store.one("SELECT status FROM messages WHERE event_id=? AND role='assistant'",(e['event_id'],))['status']))
            return dict(OFFER,role=role,packet_id='pkt_'+role)
        self.r.cognition.offer=offer;self.r.cognition.communicate=Mock(return_value=None)
        def generate(messages,cancel,deadline,*a,**k):yield 'Done.'
        self.r.pool.get=Mock(return_value=SimpleNamespace(role='C3_LANGUAGE',last_metrics={'test_seam':True},generate=generate))
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def turn(self,schedule):
        Operator(self.r).run(':observers '+schedule);self.calls.clear()
        self.r.submit('Compare plan A and plan B in detail');until=time.monotonic()+15
        while not self.r.idle() and time.monotonic()<until:time.sleep(.005)
        time.sleep(.05);return json.loads(self.r.last_answer()['metadata'])
    def test_schedules_change_physical_order_not_roles(self):
        self.assertEqual(self.r.cfg['observer_schedule'],'A_THEN_B_SEQUENTIAL')
        meta=self.turn('B_THEN_A_SEQUENTIAL');pre=[r for r,st in self.calls if st!='FINAL']
        self.assertEqual(meta['observer_schedule']['schedule'],'B_THEN_A_SEQUENTIAL');self.assertEqual(pre[:2],['B2_GIST','B1_DETAIL'])
        meta=self.turn('JEF_FIRST_THEN_BOTH')
        self.assertEqual(meta['observer_schedule']['pre'],[]);self.assertTrue(self.calls);self.assertTrue(all(st=='FINAL' for _,st in self.calls))  # only post-commit
        meta=self.turn('ON_DEMAND_REENTRY');self.assertEqual(meta['observer_schedule']['reason'],'ON_DEMAND_ONLY')
        self.assertFalse([r for r,st in self.calls if st=='FINAL'])  # no background pass either
        self.assertEqual(json.loads(Operator(self.r).run(':resources modes'))['mode'],self.r.guard.mode)

if __name__=='__main__':unittest.main()
