"""Run307 RED-first: Sleep A retention must credit an exact source-bound memory ID.

Actual Runtime/Store SQLite and actual lexical Memory.recall; no model/native.
"""
from pathlib import Path
import tempfile
import unittest

from v13.runtime import Runtime


class SleepRetentionIdentityRun307(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.question = 'RUN307 alpha main question?'
        self.e = self.r.store.event(self.r.session, self.question)
        self.a = self.r.memory.feedback(
            self.e['event_id'], 'fact', 'SAME synthetic answer', key=self.question)
        self.b = self.r.memory.feedback(
            self.e['event_id'], 'fact', 'SAME synthetic answer',
            key='RUN307 unrelated beta question?')
        self.assertNotEqual(self.a, self.b)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def probe(self):
        return self.r.sleep.cycle._probe({'event_id': self.e['event_id']})

    def test_exact_memory_identity_not_equal_value_controls_retention(self):
        self.r.cfg['memory_top_k'] = 1
        found = self.r.memory.recall(self.question, self.r.session)
        self.assertEqual(len(found), 1)
        present = found[0]['id']
        self.assertIn(present, {self.a, self.b})
        missing = ({self.a, self.b} - {present}).pop()
        self.assertEqual(found[0]['value'], 'SAME synthetic answer')

        outcome, errors, detail = self.probe()
        self.assertEqual(outcome, 'FAIL')
        self.assertIn('RECALL_MISS:' + missing, errors)
        checks = {c['memory_id']: c for c in detail['checks'] if c['probe'] == 'RECALL'}
        self.assertTrue(checks[present]['pass'])
        self.assertFalse(checks[missing]['pass'])
        self.assertIn('memory_retrieval', detail['affected_paths'])

    def test_actual_sleep_a_does_not_count_other_memory_value_as_success(self):
        self.r.cfg['memory_top_k'] = 1
        cycle = self.r.sleep.cycle
        rid = cycle.queue.enqueue(
            self.e['event_id'], 'EPISODIC', 1., 'HUMAN_CORRECTION',
            [self.e['source_ref']])
        st, _ = cycle.queue.load()
        policy = cycle.policy()
        cycle.queue.sync(st, policy)
        self.assertIn(rid, st['items'])
        # Isolate this exact event from automatic feedback replay entries.
        st['items'] = {rid: st['items'][rid]}
        report = cycle.sleep_a(st, policy, 1, stage_candidates=False)
        self.assertEqual(report['selected'], 1)
        self.assertEqual(report['passed'], 0)
        self.assertEqual(report['failed'], 1)
        self.assertEqual(report['items'][0]['outcome'], 'FAIL')
        self.assertEqual(st['items'][rid]['reps'], 0)
        self.assertEqual(st['items'][rid]['failures'], 1)
        self.assertIn('memory_retrieval', st['items'][rid]['affected_paths'])
        self.assertEqual(self.r.cfg['learning_mode'], 'RECORD_ONLY')

    def test_both_retrieved_ids_pass_and_single_memory_regression(self):
        self.r.cfg['memory_top_k'] = 2
        found = self.r.memory.recall(self.question, self.r.session)
        self.assertEqual({m['id'] for m in found}, {self.a, self.b})
        outcome, errors, detail = self.probe()
        self.assertEqual(outcome, 'PASS', errors)
        self.assertTrue(all(c['pass'] for c in detail['checks']))
        self.r.memory.forget(self.b)
        self.r.cfg['memory_top_k'] = 1
        outcome, errors, detail = self.probe()
        self.assertEqual(outcome, 'PASS', errors)
        self.assertEqual([c['memory_id'] for c in detail['checks']], [self.a])
        self.assertEqual(self.r.memory.recall(self.question, self.r.session)[0]['id'], self.a)


if __name__ == '__main__':
    unittest.main()
