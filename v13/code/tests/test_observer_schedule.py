"""§22.2.4 observer scheduling knob + §73 RSS budget as a resource-mode input (fixtures, no models)."""
import json
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from v13 import observer_schedule as obs
from v13 import latewatch as lw
from v13 import resource_modes as rm
from v13 import effort
from v13.common import Cancelled, Limits
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

    def test_recovery_slice_allows_two_roles_without_weakening_other_limits(self):
        sig=effort.signals('Compare plan A and plan B in detail',route='both')
        cfg=dict(DEFAULTS)
        recovery=effort.decide('max',sig,resource_state='NORMAL',resource_mode='GREEN',
                               observer_window_s=3.9,minimum_body_seconds=1.0,cfg=cfg,age=effort.AGE0)
        self.assertEqual(recovery['wake'],'both')
        self.assertNotIn('DEADLINE_ONE_BODY',recovery['constraints'])
        ordinary=effort.decide('max',sig,resource_state='NORMAL',resource_mode='GREEN',
                               observer_window_s=3.9,cfg=cfg,age=effort.AGE0)
        self.assertEqual(len(effort.roles(ordinary['wake'])),1)
        self.assertIn('DEADLINE_ONE_BODY',ordinary['constraints'])
        orange=effort.decide('max',sig,resource_state='PRESSURE',resource_mode='ORANGE',
                             observer_window_s=3.9,minimum_body_seconds=1.0,cfg=cfg,age=effort.AGE0)
        self.assertEqual(len(effort.roles(orange['wake'])),1)
        self.assertIn('RESOURCE_ORANGE',orange['constraints'])
        short=effort.decide('max',sig,resource_state='NORMAL',resource_mode='GREEN',
                            observer_window_s=1.9,minimum_body_seconds=1.0,cfg=cfg,age=effort.AGE0)
        self.assertEqual(len(effort.roles(short['wake'])),1)
        self.assertIn('DEADLINE_ONE_BODY',short['constraints'])

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
        # Fix the resource fixture explicitly: this test proves scheduling when both bodies are admitted,
        # not whichever resource mode the shared CI host happens to report.
        self.r.resources=lambda: {'wall_time':time.time(),'mem_available_bytes':8*1024**3,'mem_total_bytes':8*1024**3,
                                  'free_disk_bytes':20*1024**3,'battery_temperature_c':25.,'battery_percent':80.,
                                  'charging':True,'processes':[],'own_peak_rss_bytes':0}
        self.r.guard.update(self.r.resources())
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
    def test_budgeted_sequential_roles_get_fair_deadlines(self):
        now=[0.0]
        seen=[]
        def clock():
            return now[0]
        def ask(role,peer,role_end):
            seen.append((role,peer,role_end))
            # B1 finishes early; B2 receives the remaining window.
            now[0]=2.0 if role=="B1_DETAIL" else role_end
            return role
        out=obs.run(obs.plan("A_THEN_B_SEQUENTIAL",BOTH,"e"),
                    ask,10.0,Mock(),clock=clock,budgeted=True)
        self.assertEqual(out,BOTH)
        self.assertEqual([x[0] for x in seen],BOTH)
        self.assertEqual([x[1] for x in seen],[True,True])
        self.assertEqual([x[2] for x in seen],[5.0,10.0])

    def test_budgeted_short_window_defers_expired_first_role_but_keeps_peer_slice(self):
        now=[0.0]
        seen=[]
        errors=[]
        def ask(role,peer,role_end):
            available=role_end-now[0]
            seen.append((role,round(available,3)))
            if available < 1.0:
                raise Limits("pre-answer slice below role minimum")
            return role
        out=obs.run(obs.plan("A_THEN_B_SEQUENTIAL",BOTH,"e"),ask,1.5,
                    lambda role,exc:errors.append((role,type(exc).__name__)),
                    clock=lambda:now[0],budgeted=True)
        self.assertEqual(seen,[("B1_DETAIL",0.75),("B2_GIST",1.5)])
        self.assertEqual(out,["B2_GIST"])
        self.assertEqual(errors,[("B1_DETAIL","Limits")])

    def test_schedules_change_physical_order_not_roles(self):
        self.assertEqual(self.r.cfg['observer_schedule'],'A_THEN_B_SEQUENTIAL')
        meta=self.turn('B_THEN_A_SEQUENTIAL');pre=[r for r,st in self.calls if st!='FINAL']
        self.assertEqual(meta['observer_schedule']['schedule'],'B_THEN_A_SEQUENTIAL');self.assertEqual(pre[:2],['B2_GIST','B1_DETAIL'])
        meta=self.turn('JEF_FIRST_THEN_BOTH')
        self.assertEqual(meta['observer_schedule']['pre'],[]);self.assertTrue(self.calls);self.assertTrue(all(st=='FINAL' for _,st in self.calls))  # only post-commit
        meta=self.turn('ON_DEMAND_REENTRY');self.assertEqual(meta['observer_schedule']['reason'],'ON_DEMAND_ONLY')
        self.assertFalse([r for r,st in self.calls if st=='FINAL'])  # no background pass either
        self.assertEqual(json.loads(Operator(self.r).run(':resources modes'))['mode'],self.r.guard.mode)

    def test_short_c3_recovery_preserves_both_preanswer_body_slices(self):
        # 50 s gives this Runtime integration fixture a deterministic 10 s
        # pre-answer window while still reserving 40 s for C3. The 30 s
        # subminimum case is covered by the controlled scheduler regression.
        self.r.cfg["deadline_seconds"]=50
        original_rows=self.r.store.rows
        failure={"status":"DEADLINE","metadata":json.dumps({
            "runner":{"role":"C3_LANGUAGE","generated_tokens":0,"last_phase":"prefill"}
        })}
        self.r.store.rows=lambda query,args=(): (
            [failure,failure] if "SELECT status,metadata FROM messages" in query
            else original_rows(query,args)
        )
        logs=[]
        original_log=self.r.store.log
        def capture_log(kind,event,metrics):
            logs.append((kind,metrics))
            return original_log(kind,event,metrics)
        self.r.store.log=capture_log
        self.calls.clear()
        def offer(role,e,version,deadline,peer=None,valid_until=None,**kw):
            self.calls.append((role,deadline,valid_until,time.monotonic()))
            return dict(OFFER,role=role,packet_id="pkt_"+role+"_"+str(len(self.calls)))
        self.r.cognition.offer=offer
        self.r.cognition.communicate=Mock(return_value=None)
        Operator(self.r).run(":observers A_THEN_B_SEQUENTIAL")
        self.r.submit("Compare plan A and plan B in detail")
        until=time.monotonic()+15
        while not self.r.idle() and time.monotonic()<until:
            time.sleep(.005)
        pre=[x for x in self.calls if x[2] is not None]
        self.assertEqual(self.r.guard.mode,'GREEN')
        self.assertGreaterEqual(len(pre),2)
        self.assertEqual([x[0] for x in pre[:2]],BOTH)
        for _,role_deadline,turn_deadline,called_at in pre[:2]:
            self.assertLessEqual(role_deadline,turn_deadline-41.0)
            self.assertGreaterEqual(role_deadline-called_at,.99)
        decision_row=self.r.store.one("SELECT payload FROM packets WHERE kind='EffortDecision' ORDER BY rowid DESC LIMIT 1")
        decision=json.loads(decision_row['payload'])
        self.assertEqual(decision['wake'],'both')
        self.assertNotIn('DEADLINE_ONE_BODY',decision['constraints'])
        plan_logs=[m for k,m in logs if k=="native_turn_budget_plan"]
        self.assertTrue(plan_logs)
        self.assertEqual(plan_logs[0]["recent_real_prefill_failures"],2)
        self.assertGreaterEqual(plan_logs[0]["c3_reserved_seconds"],40.0)
        self.assertEqual(plan_logs[0]["focal_reserved_seconds"],1.0)

    def test_missing_peer_gets_postcommit_observation_after_partial_preanswer(self):
        self.calls.clear()
        notices=[]
        self.r.notify=notices.append
        original_decide=self.r.learner.decide
        def deterministic_decide(kind,*args,**kwargs):
            if kind=="wake":return {"learned":False,"action":"both"}
            return original_decide(kind,*args,**kwargs)
        self.r.learner.decide=deterministic_decide
        # Restore the real Cognition.offer implementation for this Runtime path;
        # the class-level fixture from setUp only records two-field tuples.
        del self.r.cognition.offer
        original_offer=self.r.cognition.offer
        self.c3_messages=[]
        def pool_get(role):
            if role=="C3_LANGUAGE":
                def generate(messages,cancel,deadline,*args,**kwargs):
                    self.c3_messages.extend(messages)
                    yield "Done."
            else:
                def generate(messages,cancel,deadline,*args,**kwargs):
                    yield json.dumps({"summary":role+" found a source-bound comparison request.",
                                      "quotes":["Compare plan A and plan B"],
                                      "uncertainty":"","needs_reentry":False})
            return SimpleNamespace(role=role,last_metrics={"status":"FINAL","prompt_tokens":64,
                "generated_tokens":1,"ttft_s":0.01,"duration_s":0.02,"actual_model":role},
                generate=generate,pids=lambda:[],memory=None)
        self.r.pool.get=Mock(side_effect=pool_get)
        def offer(role,e,version,deadline,peer=None,valid_until=None,**kw):
            row=self.r.store.one(
                "SELECT status FROM messages WHERE event_id=? AND role='assistant'",
                (e["event_id"],)
            )
            status=row["status"] if row else "MISSING"
            preanswer=kw.get("preanswer_budgeted") is True
            thread=threading.current_thread().name
            valid_until_present=valid_until is not None
            self.calls.append((role,preanswer,thread,valid_until_present,status))
            if role=="B2_GIST" and valid_until_present:
                raise Limits("pre-answer/late-watch B2 attempt expired")
            return original_offer(role,e,version,deadline,peer,valid_until=valid_until,**kw)
        self.r.cognition.offer=offer
        self.r.cognition.communicate=Mock(return_value=None)
        Operator(self.r).run(":observers A_THEN_B_SEQUENTIAL")
        with patch.object(lw,"residency",return_value=None), patch("v13.output_policy.match",return_value=None):
            self.r.submit("Compare plan A and plan B in detail")
            until=time.monotonic()+15
            while not self.r.idle() and time.monotonic()<until:
                time.sleep(.005)
        meta=json.loads(self.r.last_answer()["metadata"])
        self.assertTrue(any(role=="B1_DETAIL" and pre for role,pre,_,_,_ in self.calls))
        self.assertTrue(any(role=="B2_GIST" and pre for role,pre,_,_,_ in self.calls))
        self.assertEqual(self.r.last_answer()["status"],"FINAL",
                         msg=f"calls={self.calls!r}; notices={notices!r}; late_watch={meta.get('late_watch')!r}; error={meta.get('error')!r}; detail={meta.get('detail')!r}; failure_stage={meta.get('failure_stage')!r}")
        self.assertEqual(meta["late_watch"].get("offered"),"B2_GIST")
        self.assertEqual(meta["late_watch"].get("status"),"NO_OFFER")
        self.assertFalse(meta["late_watch"].get("offer_id"))
        self.assertTrue(any(role=="B2_GIST" and not pre and thread!="latewatch" and not valid and status=="FINAL"
                            for role,pre,thread,valid,status in self.calls),
                        msg=f"calls={self.calls!r}; late_watch={meta.get('late_watch')!r}; notices={notices!r}")
        c3_input=" ".join(message.get("content","") for message in self.c3_messages)
        self.assertIn("B1_DETAIL",c3_input)
        self.assertIn("Compare plan A and plan B",c3_input)

if __name__=='__main__':unittest.main()
