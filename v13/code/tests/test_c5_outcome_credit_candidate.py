"""Runtime and packet tests for the source-bound outcome-credit candidate."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import c5_outcome_credit_candidate as candidate


CODE = Path(__file__).resolve().parents[1]
PROBE = r'''
import json, sys, tempfile, time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from v13 import actionlearn, neuromod
from v13.inputs import record_rating
from v13.runtime import Runtime

with tempfile.TemporaryDirectory() as home:
    r=Runtime(Path(home)); r.sleep.cycle.set_policy('enabled','off')
    try:
        def gen(messages,*a,**k):yield '2 + 2 = 5'
        r._route=Mock(return_value=('simple',{'source':'TEST_ROUTE_SEAM'}))
        r.pool.get=Mock(return_value=SimpleNamespace(role='C3_LANGUAGE',last_metrics={},generate=gen))
        r.learner.output_delta=Mock(return_value=None)
        r.submit('Was ist 2 + 2?')
        until=time.monotonic()+10
        while not r.idle() and time.monotonic()<until:time.sleep(.005)
        answer=r.last_answer(); eid=answer['event_id']
        before=actionlearn.C5Learning(r.store).report()
        key=next(k for k in before['actions'] if k.endswith('|C3_LANGUAGE'))
        action=r.store.one('SELECT status FROM actions WHERE event_id=?',(eid,))
        exp=r.store.one("SELECT payload FROM packets WHERE kind='ExperienceRecord' AND event_id=?",(eid,))
        status=json.loads(exp['payload'])['outcome']
        record_rating(r.store,eid,int(sys.argv[1]),'EXPLICIT_NOTE')
        after=actionlearn.C5Learning(r.store).report()

        n=neuromod.Neuromod(r.store)
        e1=r.store.event(r.session,'cost only')['event_id']
        n.touch('candidate_cost_only',e1)
        n.signal(e1,path='candidate_cost_only',cost_error=.4)
        no_outcome=n.gate('candidate_cost_only')['delta']
        e2=r.store.event(r.session,'confirmed good')['event_id']
        n.touch('candidate_explicit',e2)
        n.signal(e2,path='candidate_explicit',source_class='real_deterministic_outcome',task_success=1.)
        good=n.gate('candidate_explicit')['delta']
        e3=r.store.event(r.session,'confirmed bad')['event_id']
        n.touch('candidate_explicit',e3)
        n.signal(e3,path='candidate_explicit',source_class='real_deterministic_outcome',task_success=0.)
        bad=n.gate('candidate_explicit')['delta']
        e4=r.store.event(r.session,'later cost only')['event_id']
        n.signal(e4,path='candidate_explicit',cost_error=.4)
        last_delta=n.gate('candidate_explicit')['delta']
        c=actionlearn.C5Learning(r.store)
        def seed_legacy(st):
            st['q']['legacy|C3_LANGUAGE']={'n':3,'mods':{'task_success':1.}}
        c._mutate(seed_legacy)
        legacy_shift=c.shifts('legacy',['C3_LANGUAGE'])[0]['C3_LANGUAGE']
        raw={'epistemic_evidence':1.,'human_correction':0.,'task_success':0.,'resource_cost':.5,'digital_prediction_error':.4}
        legacy=[neuromod.channels_from(raw|{'producer_component':p,'values_status':s}) for p,s in [
            ('F4_WORLD','measured own digital outcome; no semantic truth reward or automatic weight permission'),
            ('F6_LEARNING','measured native state target; no semantic truth label'),
            ('F4_LEARNING','human label present; task success and cost not optimizer rewards')]]
        legacy_explicit=neuromod.channels_from(raw|{'producer_component':'OLD_MEASURED'})
        print(json.dumps({'status':answer['status'],'answer_text':answer['text'],'action_status':action['status'],
            'experience_status':status,'before':before['actions'][key],
            'after':after['actions'][key],'c5_mode':before['mode'],
            'no_outcome_delta':no_outcome,'positive_delta':good,'negative_delta':bad,
            'later_cost_event':e4,'last_delta_after_cost':last_delta,'legacy_shift':legacy_shift,
            'legacy_placeholders':legacy,'legacy_explicit':legacy_explicit}))
    finally:r.close()
'''


class OutcomeCreditCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.copy = Path(cls.tmp.name)
        shutil.copytree(CODE / 'v13', cls.copy / 'v13', ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copytree(CODE / 'specs', cls.copy / 'specs')
        for name, data in candidate.build_sources(CODE / 'v13').items():
            (cls.copy / 'v13' / name).write_bytes(data)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def probe(self, code, rating=2):
        env = os.environ.copy()
        env['PYTHONPATH'] = str(code)
        proc = subprocess.run([sys.executable, '-c', PROBE, str(rating)], cwd=code,
                              env=env, text=True, capture_output=True, timeout=25)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout.strip().splitlines()[-1])

    def test_real_turn_completion_is_not_unverified_correctness(self):
        before, fixed = self.probe(CODE), self.probe(self.copy)
        for result in (before, fixed):
            self.assertEqual(result['status'], 'FINAL')
            self.assertEqual(result['answer_text'], '2 + 2 = 5')
            self.assertEqual(result['action_status'], 'FINAL')
            self.assertEqual(result['experience_status'], 'FINAL')
            self.assertEqual(result['c5_mode'], 'SHADOW')
            self.assertIn('cost_error', result['before']['modulators'])
            self.assertGreater(result['after']['modulators']['human_correction'], 0)
        self.assertEqual(before['before']['modulators']['task_success'], 1.)
        self.assertNotIn('task_success', fixed['before']['modulators'])

    def test_missing_reward_differs_from_explicit_failure(self):
        before, fixed = self.probe(CODE), self.probe(self.copy)
        self.assertLess(before['no_outcome_delta']['value'], 0)
        self.assertIsNone(fixed['no_outcome_delta'])
        self.assertGreater(fixed['positive_delta']['value'], 0)
        self.assertLess(fixed['negative_delta']['value'], 0)
        for row in fixed['legacy_placeholders']:
            self.assertNotIn('task_success', row)
            self.assertIn('evidence_gain', row)
        self.assertEqual(fixed['legacy_explicit']['task_success'], 0.)

    def test_positive_human_feedback_remains_usable(self):
        fixed = self.probe(self.copy, 10)
        self.assertEqual(fixed['after']['modulators']['human_approval'], 1.)
        self.assertEqual(fixed['after']['modulators']['human_correction'], 0.)
        self.assertNotIn('task_success', fixed['before']['modulators'])

    def test_existing_state_and_previous_delta_are_not_silently_rewritten(self):
        fixed = self.probe(self.copy)
        # Old aggregates still need an explicit, provenance-aware migration.
        self.assertGreater(fixed['legacy_shift'], 0.)
        # A later cost-only event must not be mistaken for this older outcome.
        self.assertEqual(fixed['last_delta_after_cost'], fixed['negative_delta'])
        self.assertNotEqual(fixed['last_delta_after_cost']['event_id'], fixed['later_cost_event'])

    def test_refuses_any_source_change_and_does_not_change_runtime(self):
        from hashlib import sha256
        originals = {name: (CODE / 'v13' / name).read_bytes() for name in candidate.BASE_SHA256}
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            for name, content in originals.items():
                (p / name).write_bytes(content)
            (p / 'neuromod.py').write_bytes(originals['neuromod.py'] + b'\n')
            with self.assertRaisesRegex(ValueError, 'unsupported source'):
                candidate.build_sources(p)
        for name, content in originals.items():
            self.assertEqual(sha256(content).hexdigest(), candidate.BASE_SHA256[name])
            self.assertEqual((CODE / 'v13' / name).read_bytes(), content)


if __name__ == '__main__':
    unittest.main()
