import json
from pathlib import Path
import tempfile
import time
import unittest
from v13.config import initialize
from v13.store import Store
from v13.memory import Memory
from v13.executive import Executive,MAX_EVENTS
from v13.contracts import packet
from v13.common import atomic_write

class ExecutiveChecks(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.cfg=initialize(self.home);self.s=Store(self.home);self.sid=self.s.new_session();self.x=Executive(self.s)
    def tearDown(self):self.s.close();self.tmp.cleanup()
    def event(self,text='Projekt Aurora Budget?'):
        e=self.s.event(self.sid,text);self.x.begin(e,self.sid,self.cfg);return e
    def test_continuity_restart_is_explicit_bounded_and_operator_owned(self):
        first=self.event('Entwickle Projekt Aurora');self.x.task(self.sid,'Prüfe Aurora-Budget')
        for n in range(12):last=self.event('Fortsetzung '+str(n))
        view=self.x.view(self.sid);self.assertEqual(len(view['goal_sequence']),MAX_EVENTS);self.assertEqual(view['active_task']['exact_task'],'Prüfe Aurora-Budget');self.assertEqual(view['goal'],'Fortsetzung 11')
        self.s.close();self.s=Store(self.home);self.x=Executive(self.s);self.assertEqual(self.x.view(self.sid)['active_task']['exact_task'],'Prüfe Aurora-Budget')
        other=self.s.new_session();self.assertIsNone(self.x.view(other)['active_task'])
        self.x.task(self.sid,clear=True);self.assertIsNone(self.x.view(self.sid)['active_task'])
        self.assertNotEqual(first['event_id'],last['event_id']);self.assertFalse(self.x.view(self.sid)['permission_flags']['external_tool_execution'])
    def test_implicit_task_tracks_current_turn_but_explicit_task_persists(self):
        first=self.event('Erste Frage');self.assertEqual(self.x.view(self.sid)['active_task']['exact_task'],'Erste Frage')
        second=self.event('Unabhaengige zweite Frage');view=self.x.view(self.sid)
        self.assertEqual(view['active_task']['exact_task'],'Unabhaengige zweite Frage')
        self.assertEqual(view['active_task']['source_ref'],second['source_ref'])
        self.assertEqual(view['active_task']['origin'],'SOURCE_USER_REQUEST')
        self.x.task(self.sid,'Explizite Langzeitaufgabe')
        self.event('Nebenfrage danach')
        view=self.x.view(self.sid);self.assertEqual(view['active_task']['exact_task'],'Explizite Langzeitaufgabe');self.assertEqual(view['active_task']['origin'],'EXPLICIT_OPERATOR_TASK')

    def test_task_input_and_snapshot_authority_have_hard_bounds(self):
        from v13.contracts import validate
        e=self.event();before=self.s.state('C1_EXEC:'+self.sid)
        for value in ('', 'x'*4097):
            with self.assertRaises(ValueError):self.x.task(self.sid,value)
        self.assertEqual(self.s.state('C1_EXEC:'+self.sid),before)
        p=self.x.snapshot(e,self.sid)
        with self.assertRaises(ValueError):validate('OutputSnapshot',p|{'model_generated':True})
        with self.assertRaises(ValueError):validate('OutputSnapshot',p|{'semantic_answer_available':True})
    def test_source_and_memory_revocation_are_checked_on_every_use(self):
        e=self.event();memory=Memory(self.s,self.cfg);mid=memory.feedback(e['event_id'],'fact','120 Euro');m=memory.recall('Projekt Aurora Budget?',self.sid)
        self.x.update(e,self.sid,memories=m);self.x.snapshot(e,self.sid,m)
        self.assertIn('120 Euro',self.x.report(self.sid,e));self.assertEqual(self.x.view(self.sid)['memory_refs'][0]['memory_id'],mid)
        memory.feedback(e['event_id'],'fact','200 Euro');self.assertNotIn('120 Euro',self.x.report(self.sid,e));self.assertEqual(self.x.view(self.sid)['memory_refs'],[])
        ref=e['source_ref'];atomic_write(self.home/'data/blobs'/ref['sha256'],'tamper')
        self.assertIsNone(self.x.view(self.sid)['active_task']);self.assertIn('ungültig',self.x.report(self.sid,e));self.assertNotIn('Projekt Aurora',self.x.report(self.sid,e))
    def test_offers_and_actions_keep_provenance_without_fact_authority(self):
        e=self.event();ref=e['source_ref'];offer=packet('OfferPacket','B1_DETAIL',e['event_id'],e['brain_generation_id'],[ref],role='B1_DETAIL',based_on_state_version=1,deadline_monotonic_ns=time.monotonic_ns()+10**9,evidence_refs=[ref],offer={'summary':'falscher Fakt 777','uncertainty':'Budget offen','needs_reentry':True},confidence=0.)
        self.s.add_packet('OfferPacket',offer);aid=self.s.start_action(e['event_id'],e['brain_generation_id'])
        self.x.update(e,self.sid,offers=[offer],action_id=aid,status='DEADLINE');view=self.x.view(self.sid)
        self.assertEqual(view['current_action_intent']['action_id'],aid);self.assertEqual(view['salient_B_offer'][0]['authority'],'HYPOTHESIS_NOT_FACT');self.assertEqual(view['open_questions'][0]['uncertainty'],'Budget offen')
        self.x.snapshot(e,self.sid,status='DEADLINE');report=self.x.report(self.sid,e)
        self.assertIn('SOURCE_SYSTEM_REPORT',report);self.assertNotIn('777',report);self.assertFalse(self.s.rows("SELECT * FROM memories"))
    def test_atomic_state_packet_crash_rolls_back_and_stale_update_rejected(self):
        e=self.event();before,v=self.s.state('C1_EXEC:'+self.sid)
        with self.s.tx() as c:c.execute("CREATE TRIGGER fail_exec BEFORE INSERT ON packets WHEN NEW.kind='ExecState' BEGIN SELECT RAISE(ABORT,'crash'); END")
        with self.assertRaises(Exception):self.x.update(e,self.sid,status='ERROR')
        self.assertEqual(self.s.state('C1_EXEC:'+self.sid),(before,v))
        with self.s.tx() as c:c.execute('DROP TRIGGER fail_exec')
        other=self.event('Andere Aufgabe')
        with self.assertRaises(ValueError):self.x.update(e,self.sid,status='FINAL')
        self.assertEqual(self.x.view(self.sid)['last_event_id'],other['event_id'])
    def test_control_boundary_consumes_binding_permissions_pressure_and_versions(self):
        e=self.event();p=self.x.control_context(e,self.sid)
        self.assertTrue(self.x.control_admissible(p,e,self.sid,'Projekt Aurora Budget?')[0]);self.assertFalse(self.x.control_admissible(p,e,self.sid,'Andere Quelle')[0])
        modified=p|{'external_action_authority':True};self.assertFalse(self.x.control_admissible(modified,e,self.sid,'Projekt Aurora Budget?')[0])
        pressure=self.x.control_context(e,self.sid,'PRESSURE');self.assertEqual(self.x.control_admissible(pressure,e,self.sid,'Projekt Aurora Budget?')[1],'RESOURCE_CONTROL_ABSTENTION')
        self.x.update(e,self.sid,status='FINAL');self.assertEqual(self.x.control_admissible(p,e,self.sid,'Projekt Aurora Budget?')[1],'STALE_CONTROL_CONTEXT')
    def test_event_session_and_snapshot_stay_bound_after_restart(self):
        e=self.event();self.x.snapshot(e,self.sid,status='WAITING');other=self.s.new_session()
        with self.assertRaises(ValueError):self.x.begin(e,other,self.cfg)
        with self.assertRaises(ValueError):self.x.report(other,e)
        self.s.close();self.s=Store(self.home);self.x=Executive(self.s)
        self.assertIn('Projekt Aurora Budget?',self.x.report(self.sid));self.assertIn('keine Modellantwort',self.x.report(self.sid));self.assertNotIn('Projekt Aurora',self.x.report(other))

class ExecutiveRuntimeChecks(unittest.TestCase):
    def setUp(self):
        from v13.runtime import Runtime
        from v13.operator import Operator
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.r=Runtime(self.home);self.r.cfg['observer_mode']='off';self.op=Operator(self.r)
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def wait(self):
        until=time.monotonic()+5
        while not self.r.idle() and time.monotonic()<until:time.sleep(.01)
        self.assertTrue(self.r.idle())
    def test_real_missing_model_failure_has_source_snapshot_and_continuity(self):
        self.r.submit('Projekt Aurora Budget?');self.wait();row=self.r.last_answer();meta=json.loads(row['metadata'])
        self.assertEqual(row['status'],'ERROR');self.assertIn('SOURCE_SYSTEM_REPORT',row['text']);self.assertIn('Projekt Aurora Budget?',row['text']);self.assertFalse(meta['model_generated']);self.assertTrue(meta['context_source_refs'])
        state=json.loads(self.op.run(':executive'));self.assertEqual(state['goal'],'Projekt Aurora Budget?');self.assertEqual(state['uncertainty']['report'],'ERROR')
        self.assertIn('Projekt Aurora Budget?',self.op.run(':force-report'));self.assertTrue(state['memory_refs']==[])
    def test_force_report_before_any_native_output_ends_deliberation(self):
        import threading
        reached=threading.Event();release=threading.Event();original=self.r.cognition.percept
        def delayed(e):
            reached.set();release.wait(2);return original(e)
        self.r.cognition.percept=delayed
        try:
            self.r.submit('Quellengebundene Aufgabe ohne Modell');self.assertTrue(reached.wait(1));before=time.monotonic();report=self.op.run(':force-report')
            self.assertLess(time.monotonic()-before,.5);self.assertIn('Quellengebundene Aufgabe ohne Modell',report);self.assertIn('keine Modellantwort',report);self.assertTrue(self.r.cancel_event.is_set())
        finally:release.set()
        self.wait();self.assertEqual(self.r.last_answer()['status'],'CANCELLED');self.assertFalse(json.loads(self.r.last_answer()['metadata'])['model_generated'])
    def test_idle_force_report_preserves_best_actual_saved_output(self):
        self.r.submit('Kopiere exakt: Exakte Ausgabe 123');self.wait();row=self.r.last_answer()
        report=self.op.run(':force-report');self.assertIn('CURRENT_OUTPUT_SNAPSHOT',report);self.assertIn(row['text'],report)
        self.assertEqual(self.r.last_answer(),row)
    def test_c2_resource_guard_abstains_without_native_or_head_execution(self):
        e=self.r.store.event(self.r.session,'Hallo');self.r.executive.begin(e,self.r.session,self.r.cfg);self.r.guard.state='PRESSURE'
        def forbidden(*args,**kwargs):raise AssertionError('Native execution was not permitted')
        self.r.needle.control=forbidden;self.r.learner.propose=forbidden
        route,info=self.r._route('Hallo',e,time.monotonic()+1)
        self.assertEqual(route,'simple');self.assertEqual(info['executive_control_abstention'],'RESOURCE_CONTROL_ABSTENTION')

if __name__=='__main__':unittest.main()
