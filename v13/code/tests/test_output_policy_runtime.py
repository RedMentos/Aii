"""Real coordinator/SQLite integration. Native seams are spies, not model proof."""
import json
import shlex
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from v13.history import native_history
from v13.operator import Operator
from v13.runtime import Runtime


class OutputPolicyRuntime(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def wait(self):
        until = time.monotonic() + 5
        while not self.r.idle() and time.monotonic() < until:
            time.sleep(.005)
        self.assertTrue(self.r.idle())
        return self.r.last_answer()

    def approve(self, query='Regel?', answer='Genau. 👨‍👩‍👧‍👦'):
        op = Operator(self.r)
        rid = op.run(':rules fixed ' + shlex.quote(query) + ' ' + shlex.quote(answer)).split(';')[0]
        op.run(':approve ' + rid)

    def native_spies(self):
        calls = []
        for obj, attr in ((self.r.pool, 'get'), (self.r.needle, 'embed'),
                          (self.r.needle, 'control'), (self.r.cognition, 'percept'),
                          (self.r.cognition, 'offer'), (self.r.memory, 'recall'),
                          (self.r.learner, 'decide'), (self.r.learner, 'output_delta'),
                          (self.r.learner, 'world_predict')):
            spy = Mock(side_effect=AssertionError('Forbidden native path: ' + attr))
            setattr(obj, attr, spy)
            calls.append(spy)
        return calls

    def test_fixed_turn_has_no_foreground_or_background_native_calls(self):
        self.approve()
        before = self.r.store.generation_id
        spies = self.native_spies()
        eid = self.r.submit('Regel?')
        row = self.wait()
        self.assertEqual((row['text'], row['status']), ('Genau. 👨‍👩‍👧‍👦', 'FINAL'))
        meta = json.loads(row['metadata'])
        self.assertFalse(meta['model_generated'])
        self.assertEqual(meta['output_authority'], 'APPROVED_FIXED_RULE')
        self.assertTrue(meta['exact_policy_matched'])
        self.assertIn('NATIVE_WORLD_PREDICTION', meta['skipped_native_stages'])
        self.assertTrue(all(x.call_count == 0 for x in spies))
        self.assertEqual(self.r.store.generation_id, before)
        policy = json.loads(self.r.store.one("SELECT payload FROM packets WHERE event_id=? AND kind='OutputPolicyDecision'", (eid,))['payload'])
        self.assertFalse(policy['model_generated'])
        self.assertEqual(self.r.store.read_source(policy['answer_ref']), row['text'])
        for kind in ('PerceptPacket', 'JEFBroadcastPacket', 'CorollaryCopy', 'ActionOutcome', 'PredictionOutcome', 'ExperienceRecord'):
            self.assertTrue(self.r.store.one('SELECT id FROM packets WHERE event_id=? AND kind=?', (eid, kind)), kind)
        self.assertEqual(self.r.store.one('SELECT state FROM accepted_turns WHERE event_id=?', (eid,))['state'], 'DONE')
        self.assertEqual(self.r.store.integrity(True), [])

    def test_restart_repeat_preserves_exact_answer_and_approved_source(self):
        answer = 'نعم\nGenau\t🍎'
        self.approve(answer=answer)
        version = self.r.store.generation()['rule_version']
        for i in range(2):
            spies = self.native_spies()
            self.r.submit('Regel?')
            row = self.wait()
            self.assertEqual(row['text'].encode(), answer.encode())
            self.assertEqual(json.loads(row['metadata'])['output_policy']['rule_version'], version)
            self.assertTrue(all(x.call_count == 0 for x in spies))
            if i == 0:
                self.r.close()
                self.r = Runtime(self.home)

    def test_pending_or_unmatched_rule_keeps_regular_route(self):
        op = Operator(self.r)
        rid = op.run(':rules fixed "Regel?" "Genau."').split(';')[0]
        self.r._route = Mock(return_value=('simple', {'source': 'TEST_ROUTE_SEAM'}))
        self.r.cfg['observer_mode'] = 'off'
        self.r.pool.get = Mock(side_effect=RuntimeError('Native transport test seam'))
        self.r.submit('Regel?')
        row = self.wait()
        self.assertEqual(row['status'], 'ERROR')
        self.r._route.assert_called_once()
        self.assertNotIn('exact_policy_matched', json.loads(row['metadata']))
        op.run(':approve ' + rid)
        self.r._route.reset_mock()
        self.r.submit('Regel? ')
        self.wait()
        self.r._route.assert_called_once()

    def test_tampered_active_source_fail_closed_and_no_model_generated_claim(self):
        self.approve()
        rule = self.r.store.rules()[0]
        (self.home / 'data/blobs' / rule['answer_ref']['sha256']).write_text('tamper')
        spies = self.native_spies()
        self.r.submit('Andere Frage')
        row = self.wait()
        meta = json.loads(row['metadata'])
        self.assertEqual(row['status'], 'ERROR')
        self.assertEqual(meta['failure_stage'], 'policy_check')
        self.assertEqual(meta['output_authority'], 'SOURCE_SYSTEM_REPORT')
        self.assertFalse(meta['model_generated'])
        self.assertTrue(row['text'].strip())
        self.assertTrue(all(x.call_count == 0 for x in spies))

    def test_rule_removal_excludes_old_answer_from_native_history(self):
        self.approve()
        self.r.submit('Regel?')
        row = self.wait()
        records, refs = native_history(self.r.store, self.r.session, 'next', 4)
        self.assertEqual(len(records), 2)
        self.assertTrue(refs)
        op = Operator(self.r)
        rid = op.run(':rules remove 0').split(';')[0]
        op.run(':approve ' + rid)
        self.assertEqual(native_history(self.r.store, self.r.session, 'next', 4), ([], []))
        self.assertEqual(self.r.store.one('SELECT text FROM messages WHERE id=?', (row['id'],))['text'], row['text'])

    def streamed_turn(self, chunks):
        self.r.cfg['observer_mode'] = 'off'
        self.r._route = Mock(return_value=('simple', {'source': 'TEST_ROUTE_SEAM'}))
        runner = SimpleNamespace(role='C3_LANGUAGE', last_metrics={'transport_test_seam': True},
                                 generate=lambda *args, **kwargs: iter(chunks))
        self.r.pool.get = Mock(return_value=runner)
        self.r.learner.output_delta = Mock(return_value=None)
        self.r.submit('Prüfe den Transport')
        return self.wait()

    def test_all_invisible_transport_output_becomes_visible_system_report(self):
        row = self.streamed_turn(['\x1b\u202e', '\u200d  \t'])
        meta = json.loads(row['metadata'])
        self.assertEqual(row['status'], 'ERROR')
        self.assertFalse(meta['model_generated'])
        self.assertEqual(meta['output_authority'], 'SOURCE_SYSTEM_REPORT')
        self.assertEqual(meta['output_removed_characters'], 2)
        self.assertIn('keinen sichtbaren Text', meta['detail'])
        self.assertNotIn('\u202e', row['text'])

    def test_visible_transport_keeps_spacing_multilingual_and_counts_controls(self):
        row = self.streamed_turn(['  \t', '\x1b\u202e', 'Hallo نعم 👨‍👩‍👧‍👦', '\n'])
        self.assertEqual(row['status'], 'FINAL')
        self.assertEqual(row['text'], '  \tHallo نعم 👨‍👩‍👧‍👦\n')
        meta = json.loads(row['metadata'])
        self.assertTrue(meta['model_generated'])
        self.assertEqual(meta['output_removed_characters'], 2)
        self.assertIsNotNone(meta['first_output_monotonic_ns'])


if __name__ == '__main__':
    unittest.main()
