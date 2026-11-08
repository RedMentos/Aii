"""One real Store/Runtime flow across feedback, episodic association and replay."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from scripts.c5_outcome_credit_candidate import build_sources as build_credit_sources
from scripts.correction_association_integration_candidate import build_sources as build_association_sources


CODE = Path(__file__).resolve().parents[1]
PROBE = r'''
import json, sys, tempfile, time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from v13 import actionlearn, c5_feedback_shadow_store_candidate as shadow, inputs
from v13.correction_association_shadow_candidate import rollback
from v13.operator import Operator
from v13.runtime import Runtime

mode = sys.argv[1]
enabled = mode in ('on', 'unrated')
rated = mode != 'unrated'
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
        if enabled:
            op = Operator(r)
            op.run(':c5 feedback-shadow on')
            op.run(':episodes correction-association shadow')
        seed_event = r.store.event(session, 'Project Ember budget')
        seed = r.memory.feedback(seed_event['event_id'], 'fact', '120 credits', key='Project Ember budget')
        eid, first, first_meta = turn(r, 'What are Project Ember budget and launch date?')
        c5_before = actionlearn.C5Learning(r.store).report()['actions']
        key = next(k for k in c5_before if k.endswith('|C3_LANGUAGE'))
        correction = r.memory.feedback(eid, 'fact', '8 April', key='Project Ember launch date')
        if rated: inputs.record_rating(r.store, eid, 2, 'EXPLICIT_NOTE')
        c5_after = actionlearn.C5Learning(r.store).report()['actions'][key]
        feedback = shadow.view(r.store, session)
        cycle = r.sleep.cycle
        state, version = cycle.queue.load(); policy = cycle.policy()
        cycle.queue.sync(state, policy)
        replay = cycle.sleep_a(state, policy, 8, stage_candidates=False)
        cycle.queue.save(state, version)
        _, second, second_meta = turn(r, 'What is Project Ember budget?')
        r.close(); r = Runtime(Path(home)); wire(r)
        if r.session != session: raise RuntimeError('session not restored')
        restart_eid, _, restart_meta = turn(r, 'What is Project Ember budget?')
        selected = r.store.one("SELECT payload FROM packets WHERE kind='ActionSelection' AND event_id=? "
                               "AND json_extract(payload,'$.stage')='COMMIT' ORDER BY rowid DESC LIMIT 1", (restart_eid,))
        selection = json.loads(selected['payload'])
        selection_learning = selection['learning']
        after_restart = shadow.view(r.store, session)
        removed = rollback(r.store, correction)['removed'] if enabled else 0
        _, _, rollback_meta = turn(r, 'What is Project Ember budget?')
        print(json.dumps({'seed':seed,'correction':correction,
             'first_ids':[x['memory_id'] for x in first_meta['memory_retrieval']],
             'second_ids':[x['memory_id'] for x in second_meta['memory_retrieval']],
             'second_shadow':second_meta.get('correction_association_shadow',[]),
             'restart_shadow':restart_meta.get('correction_association_shadow',[]),
             'rollback_shadow':rollback_meta.get('correction_association_shadow',[]),
             'removed':removed,'feedback':feedback,'feedback_restart':after_restart,
             'c5_before':c5_before[key], 'c5_after':c5_after,
             'selection_learning':selection_learning,
             'selected_action':selection['selected']['action_id'],
             'c5_mode':actionlearn.C5Learning(r.store).report()['mode'],
             'replay_pass':any(x.get('outcome')=='PASS' for x in replay['items']),
             'answer':second['text'],'learning_mode':r.cfg['learning_mode'],
             'updates':len(r.store.rows('SELECT * FROM updates'))}))
    finally: r.close()
'''


class ConnectedFeedbackMemoryReplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.copy = Path(cls.tmp.name)
        shutil.copytree(CODE / 'v13', cls.copy / 'v13', ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copytree(CODE / 'specs', cls.copy / 'specs')
        for builder in (build_credit_sources, build_association_sources):
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

    def test_one_correction_reaches_feedback_and_replayed_association(self):
        off, on, unrated = self.scenario('off'), self.scenario('on'), self.scenario('unrated')
        for result in (off, on, unrated):
            self.assertIn(result['seed'], result['first_ids'])
            self.assertIn(result['seed'], result['second_ids'])
            self.assertNotIn(result['correction'], result['second_ids'])
            self.assertTrue(result['replay_pass'])
            self.assertEqual(result['answer'], 'I do not know.')
            self.assertEqual(result['learning_mode'], 'RECORD_ONLY')
            self.assertEqual(result['c5_mode'], 'SHADOW')
            self.assertEqual(result['selected_action'], result['selection_learning']['boot'])
            self.assertEqual(result['updates'], 0)
            self.assertNotIn('task_success', result['c5_before']['modulators'])
        for result in (off, on):
            self.assertGreater(result['c5_after']['modulators']['human_correction'], 0)
        self.assertNotIn('human_correction', unrated['c5_after']['modulators'])
        self.assertEqual((off['feedback']['events'], off['second_shadow']), (0, []))
        self.assertEqual(on['feedback']['events'], 1)
        self.assertEqual(on['feedback']['origin_counts']['EXPLICIT_NOTE'], 1)
        self.assertEqual(on['feedback']['learning_authority'], 0)
        self.assertEqual(unrated['feedback']['events'], 0)
        self.assertEqual(on['feedback_restart'], on['feedback'])
        self.assertEqual([x['memory_id'] for x in on['second_shadow']], [on['correction']])
        self.assertEqual([x['memory_id'] for x in on['restart_shadow']], [on['correction']])
        self.assertEqual((on['removed'], on['rollback_shadow']), (1, []))
        self.assertLess(on['selection_learning']['shifts']['C3_LANGUAGE'],
                        unrated['selection_learning']['shifts']['C3_LANGUAGE'])


if __name__ == '__main__':
    unittest.main()
