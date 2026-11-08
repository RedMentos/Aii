"""Compose the reviewed AG4, C5 and replay candidates on one isolated Runtime."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from scripts.ag4_outcome_crosspath_candidate import build_sources as build_ag4_sources
from scripts.c5_outcome_credit_candidate import build_sources as build_credit_sources
from scripts.correction_association_integration_candidate import build_sources as build_memory_sources


CODE = Path(__file__).resolve().parents[1]
PROBE = r'''
import json, sys, tempfile, time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from v13 import actionlearn, c5_feedback_shadow_store_candidate as shadow, inputs
from v13.agi import hub
from v13.operator import Operator
from v13.runtime import Runtime

enabled = sys.argv[1] == 'on'
def wire(r):
    r.sleep.cycle.set_policy('enabled', 'off')
    r._route = Mock(return_value=('simple', {'source': 'TEST_ROUTE_SEAM'}))
    r.pool.get = Mock(return_value=SimpleNamespace(role='C3_LANGUAGE', last_metrics={},
                                                    generate=lambda *a, **k: iter(['I do not know.'])))
    r.learner.output_delta = Mock(return_value=None)
def turn(r, text):
    eid = r.submit(text)
    deadline = time.monotonic() + 10
    while not r.idle() and time.monotonic() < deadline: time.sleep(.005)
    row = r.last_answer()
    if not row or row['event_id'] != eid or row['status'] != 'FINAL': raise RuntimeError('turn failed')
    return eid, row, json.loads(row['metadata'])

with tempfile.TemporaryDirectory() as home:
    r = Runtime(Path(home)); wire(r)
    try:
        session = r.session
        skills = hub(r).skills
        skills.propose('ember_route', [{'route': 'simple'}], trigger='project ember')
        skills.set_stage('ember_route', 'TRUSTED')
        if enabled:
            op = Operator(r)
            op.run(':c5 feedback-shadow on')
            op.run(':episodes correction-association shadow')
        seed_event = r.store.event(session, 'Project Ember budget')
        seed = r.memory.feedback(seed_event['event_id'], 'fact', '120 credits', key='Project Ember budget')
        eid, first, meta = turn(r, 'What are Project Ember budget and launch date?')
        at_final = skills.get('ember_route')
        c5_before = actionlearn.C5Learning(r.store).report()['actions']
        key = next(k for k in c5_before if k.endswith('|C3_LANGUAGE'))
        inputs.record_rating(r.store, eid, 8, 'IMPLICIT_CHAT')
        after_implicit = skills.get('ember_route')
        with patch('v13.jefbridge.on_rating', side_effect=RuntimeError('test seam')):
            inputs.record_rating(r.store, eid, 8 if sys.argv[1] == 'positive' else 2, 'EXPLICIT_NOTE')
        after_explicit = skills.get('ember_route')
        c5_after = actionlearn.C5Learning(r.store).report()['actions'][key]
        correction = r.memory.feedback(eid, 'fact', '8 April', key='Project Ember launch date')
        after_fact = skills.get('ember_route')
        feedback = shadow.view(r.store, session)
        cycle = r.sleep.cycle
        state, version = cycle.queue.load(); policy = cycle.policy()
        cycle.queue.sync(state, policy)
        replay = cycle.sleep_a(state, policy, 8, stage_candidates=False)
        cycle.queue.save(state, version)
        _, second, second_meta = turn(r, 'What is Project Ember budget?')
        r.close(); r = Runtime(Path(home)); wire(r)
        if r.session != session: raise RuntimeError('session not restored')
        persisted_skill = hub(r).skills.get('ember_route')
        persisted_feedback = shadow.view(r.store, session)
        _, _, restart_meta = turn(r, 'What is Project Ember budget?')
        print(json.dumps({'used_skill':meta.get('skill',{}).get('name'),
             'seed':seed,'correction':correction,
             'first_ids':[x['memory_id'] for x in meta['memory_retrieval']],
             'second_shadow':second_meta.get('correction_association_shadow',[]),
             'restart_shadow':restart_meta.get('correction_association_shadow',[]),
             'at_final':[at_final['uses'],at_final['successes']],
             'after_implicit':[after_implicit['uses'],after_implicit['successes']],
             'after_explicit':[after_explicit['uses'],after_explicit['successes']],
             'after_fact':[after_fact['uses'],after_fact['successes']],
             'after_restart':[persisted_skill['uses'],persisted_skill['successes']],
             'feedback':feedback,'persisted_feedback':persisted_feedback,
             'c5_before':c5_before[key],'c5_after':c5_after,
             'replay_pass':any(x.get('outcome')=='PASS' for x in replay['items']),
             'answer':second['text'],'learning_mode':r.cfg['learning_mode'],
             'updates':len(r.store.rows('SELECT * FROM updates'))}))
    finally: r.close()
'''


class MultiOrganCorrection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.copy = Path(cls.tmp.name)
        shutil.copytree(CODE / 'v13', cls.copy / 'v13', ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copytree(CODE / 'specs', cls.copy / 'specs')
        for builder in (build_credit_sources, build_memory_sources, build_ag4_sources):
            for name, data in builder(CODE / 'v13').items():
                (cls.copy / 'v13' / name).write_bytes(data)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def scenario(self, mode):
        env = os.environ.copy()
        env['PYTHONPATH'] = str(self.copy)
        proc = subprocess.run([sys.executable, '-c', PROBE, mode], cwd=self.copy,
                              env=env, text=True, capture_output=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout.strip().splitlines()[-1])

    def test_one_correction_reaches_ag4_c5_and_replayed_memory(self):
        off, on = self.scenario('off'), self.scenario('on')
        for result in (off, on):
            self.assertEqual(result['used_skill'], 'ember_route')
            self.assertIn(result['seed'], result['first_ids'])
            self.assertEqual(result['at_final'], [0, 0])
            self.assertEqual(result['after_implicit'], [0, 0])
            self.assertEqual(result['after_explicit'], [1, 0])
            self.assertEqual(result['after_fact'], [1, 0])
            self.assertEqual(result['after_restart'], [1, 0])
            self.assertNotIn('task_success', result['c5_before']['modulators'])
            self.assertGreater(result['c5_after']['modulators']['human_correction'], 0)
            self.assertTrue(result['replay_pass'])
            self.assertEqual(result['answer'], 'I do not know.')
            self.assertEqual(result['learning_mode'], 'RECORD_ONLY')
            self.assertEqual(result['updates'], 0)
        self.assertEqual((off['feedback']['events'], off['second_shadow']), (0, []))
        self.assertEqual(on['feedback']['events'], 1)
        self.assertEqual(on['feedback']['origin_counts'], {'EXPLICIT_NOTE': 1, 'IMPLICIT_CHAT': 1})
        self.assertEqual(on['feedback']['learning_authority'], 0)
        self.assertEqual(on['persisted_feedback'], on['feedback'])
        effective = next(iter(on['feedback']['by_action'].values()))
        self.assertGreater(effective['human_correction'], 0)
        self.assertEqual(effective['human_approval'], 0)
        self.assertEqual([x['memory_id'] for x in on['second_shadow']], [on['correction']])
        self.assertEqual([x['memory_id'] for x in on['restart_shadow']], [on['correction']])

    def test_positive_human_credit_retracted_by_fact_correction_after_restart(self):
        # A positive explicit rating is provisional evidence, not irrevocable truth.
        # The subsequent source-bound fact correction must retract that same
        # event's AG4 success without counting a second skill use.
        result = self.scenario('positive')
        self.assertEqual(result['used_skill'], 'ember_route')
        self.assertEqual(result['at_final'], [0, 0])
        self.assertEqual(result['after_implicit'], [0, 0])
        self.assertEqual(result['after_explicit'], [1, 1])
        self.assertEqual(result['after_fact'], [1, 0])
        self.assertEqual(result['after_restart'], [1, 0])
        self.assertEqual(result['learning_mode'], 'RECORD_ONLY')
        self.assertEqual(result['updates'], 0)
        self.assertTrue(result['replay_pass'])
        self.assertEqual(result['answer'], 'I do not know.')
        self.assertEqual(result['feedback']['events'], 0)  # shadow was off

    def test_source_and_patch_mismatch_fail_closed(self):
        with tempfile.TemporaryDirectory() as home:
            source = Path(home) / 'v13'
            shutil.copytree(CODE / 'v13', source, ignore=shutil.ignore_patterns('__pycache__'))
            original = (source / 'agi/live.py').read_bytes()
            build_ag4_sources(source)
            self.assertEqual((source / 'agi/live.py').read_bytes(), original)
            (source / 'agi/live.py').write_bytes(original + b'\n# changed\n')
            with self.assertRaises(ValueError):
                build_ag4_sources(source)
            (source / 'agi/live.py').write_bytes(original)
            bad_patch = Path(home) / 'bad.patch'
            bad_patch.write_bytes(b'changed')
            with self.assertRaises(ValueError):
                build_ag4_sources(source, bad_patch)


if __name__ == '__main__':
    unittest.main()
