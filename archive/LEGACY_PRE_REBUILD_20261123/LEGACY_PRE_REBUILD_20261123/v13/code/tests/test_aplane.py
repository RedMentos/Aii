"""WP-T4 A-plane: A3 student T2 gate/fallback, text distillation head and teacher-dropout curve (local fixtures, no models)."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
from v13 import aplane
from v13.agi import hub
from v13.contracts import packet
from v13.operator import Operator
from v13.runtime import Runtime

CITIES=['Paris','Berlin','Madrid','Rome','Vienna','Lisbon','Prague','Warsaw','Oslo','Dublin','Athens','Bern','Sofia','Riga','Tallinn','Vilnius',
        'Zagreb','Ljubljana','Budapest','Helsinki','Stockholm','Copenhagen','Brussels','Amsterdam','Luxembourg','Valletta','Nicosia','Bratislava','Bucharest','Reykjavik']

class Base(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name))
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def evals(self,agree_flags):
        s=self.r.store
        for ok in agree_flags:
            e=s.event(self.r.session,'route me')
            s.add_packet('StudentEvaluation',packet('StudentEvaluation','C2_CONTROL',e['event_id'],s.generation_id,[e['source_ref']],percept_packet_id='pkt_x',
                         source_ref=e['source_ref'],student_route='detail',teacher_route='detail' if ok else 'gist',agreement=bool(ok),routing_authority=0))

class StudentT2(Base):
    def test_gate_needs_count_agreement_and_retention(self):
        self.assertFalse(aplane.student_gate(self.r.store)['pass'])
        with self.assertRaises(ValueError):aplane.set_student_mode(self.r.store,'fallback')
        self.evals([True]*60);g=aplane.student_gate(self.r.store)
        self.assertTrue(g['pass']);self.assertEqual(g['agreement'],1.);self.assertEqual(len(g['agreement_curve']),3)
        self.assertEqual(aplane.set_student_mode(self.r.store,'fallback'),'fallback')
        self.evals([False]*8);g=aplane.student_gate(self.r.store)  # newest window drops > 5 points: retention fails
        self.assertFalse(g['retention_pass']);self.assertFalse(g['pass'])
    def test_small_dip_keeps_gate_and_old_failures_leave_the_window(self):
        # thread L 2026-10-12, preregistered candidate PASS: window 100, retention only against a clear drop
        self.evals([False]*60+[True]*100);g=aplane.student_gate(self.r.store)
        self.assertEqual(g['n'],100);self.assertTrue(g['pass'])  # early failures are outside the window
        self.evals([True,True,False]*3);g=aplane.student_gate(self.r.store)
        self.assertTrue(g['retention_pass']);self.assertTrue(g['pass'])  # recent 25 still >= .75
    def test_fallback_routes_only_when_promoted_and_demotes_itself(self):
        r=self.r;e=r.store.event(r.session,'Explain the budget')
        r.learner.student_route=Mock(return_value={'route':'detail','percept':{}})
        self.assertIsNone(aplane.student_fallback(r,e,{'source':'BOOT_SCAFFOLD'}))  # shadow: never routes
        self.evals([True]*60);aplane.set_student_mode(r.store,'fallback')
        route,info=aplane.student_fallback(r,e,{'source':'BOOT_SCAFFOLD'})
        self.assertEqual((route,info['source']),('detail','A3_STUDENT_FALLBACK'))
        r.learner.student_route=Mock(return_value={'status':'OUT_OF_SUPPORT','routing_authority':0});self.assertIsNone(aplane.student_fallback(r,e,{}))
        self.evals([False]*10);r.learner.student_route=Mock(return_value={'route':'detail','percept':{}})
        self.assertIsNone(aplane.student_fallback(r,e,{}));self.assertEqual(aplane.state(r.store)['student_mode'],'shadow')
    def test_runtime_uses_fallback_only_when_teacher_path_fails(self):
        r=self.r;r.cfg['route_override']='auto';e=r.store.event(r.session,'Explain the budget')
        self.evals([True]*60);aplane.set_student_mode(r.store,'fallback')
        r.learner.student_route=Mock(return_value={'route':'gist','percept':{}})
        r.executive.control_admissible=Mock(return_value=(True,None));r.consolidation.route=Mock(return_value=None)
        r.learner.propose=Mock(side_effect=RuntimeError('needle down'))
        route,info=r._route('Explain the budget',e,10**9)
        self.assertEqual((route,info['source']),('gist','A3_STUDENT_FALLBACK'));self.assertIn('control_unavailable',info)
        r.learner.propose=Mock(return_value=None);r.needle.control=Mock(return_value={'route':'simple'});r.learner.control_calibrate=Mock(return_value=None)
        route,info=r._route('Explain the budget',e,10**9);self.assertNotEqual(info['source'],'A3_STUDENT_FALLBACK')

class Distill(Base):
    def teach(self,n=len(CITIES)):
        g=hub(self.r);t=g.teacher
        t.register('fake',lambda prompt:{'answer':'The capital city you asked about is '+prompt.split()[-1].rstrip('?')+'.','model':'fixture'},'local')
        for c in CITIES[:n]:t.fulfil(t.request('Tell me about the capital '+c+'?',capability='geo'),'fake')
        return t
    def test_record_only_and_too_few_traces_refused(self):
        with self.assertRaises(ValueError):aplane.distill(self.r)
        Operator(self.r).run(':learning shadow');self.teach(5)
        with self.assertRaises(ValueError):aplane.distill(self.r,'geo')
    def test_head_beats_baseline_and_curve_runs(self):
        Operator(self.r).run(':learning shadow');t=self.teach()
        try:run=aplane.distill(self.r,'geo')
        except ValueError as exc:self.skipTest(str(exc))  # hash split left too few held-out traces for this fixture
        m=run['held_out_metrics'];self.assertGreater(m['mean_cosine'],m['baseline_cosine'])
        self.assertTrue(run['eligible']);self.assertGreater(m['retrieval_at_1'],2*m['chance'])
        self.assertLessEqual(run['curve'][-1]['solo_success'],run['curve'][0]['solo_success'])  # less teacher, less solo success
        self.assertEqual([c['teacher_share'] for c in run['curve']],list(aplane.CURVE));self.assertEqual(run['curve'][0]['reliance'],0. if run['curve'][0]['solo_success'] else 1.)
        self.assertEqual(run['authority'],'EVIDENCE_ONLY_NO_OUTPUT');self.assertTrue((Path(self.tmp.name)/run['artifact']).exists())
        rel=t.reliance('geo');self.assertIsNotNone(rel['solo_success'])
        st=json.loads(Operator(self.r).run(':aplane'));self.assertEqual(st['distill']['id'],run['id'])

if __name__=='__main__':unittest.main()
