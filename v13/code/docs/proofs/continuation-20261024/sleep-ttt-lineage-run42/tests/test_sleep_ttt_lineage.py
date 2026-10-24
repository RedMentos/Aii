"""Synthetic, isolated tests; these do not exercise the full V13 runtime."""
import json
import tempfile
import threading
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from sleep_ttt_lineage_candidate import _stage


class FakeStore:
    def __init__(self):
        self.mutex = threading.RLock()
        self.entries = {'A': [], 'B': []}
        self.records = {'A': [], 'B': []}
        self.revoked = set()
        self.history_failure = set()

    def state(self):
        return {'sessions': {s: {'entries': es} for s, es in self.entries.items()}}, 1

    def history(self, _store, session, _event, _turns):
        if session in self.history_failure:
            raise ValueError('revoked dependency')
        return [r for r in self.records[session] if r['event_id'] not in self.revoked], []

    def add(self, session, eid, idx, user, answer, generated=True):
        self.entries[session].append({'event_id': eid, 'msg': idx,
                                      'user': user, 'answer': answer})
        self.records[session].extend([
            {'event_id': eid, 'session_id': session, 'role': 'user',
             'text': user, 'status': 'FINAL', 'id': idx-1, 'metadata': '{}'},
            {'event_id': eid, 'session_id': session, 'role': 'assistant',
             'text': answer, 'status': 'FINAL', 'id': idx,
             'metadata': json.dumps({'model_generated': generated})}])


def compress(text, cap):
    return text, [], True


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(text, encoding='utf-8')
    temp.replace(path)


class Lineage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.s = FakeStore()
        self.s.add('A', 'e1', 2, 'private old', 'old answer')
        self.s.add('A', 'e2', 4, 'second', 'second answer')
        self.s.add('A', 'e3', 6, 'third', 'third answer')

    def tearDown(self):
        self.tmp.cleanup()

    def run_stage(self, checkpoint=None):
        return _stage(self.s, self.home, checkpoint, self.s.history,
                      compress, write, lambda x: json.dumps(x, sort_keys=True),
                      lambda store: store.state())

    def read(self):
        return [json.loads(x) for x in (self.home / 'exports/sleep-ttt-candidates.jsonl').read_text().splitlines()]

    def test_valid_stages_two_later_targets_with_context(self):
        result = self.run_stage()
        self.assertEqual(result['candidates'], 2)
        self.assertEqual([x['event_id'] for x in self.read()], ['e2', 'e3'])
        self.assertIn('private old', self.read()[0]['context'])
        self.assertEqual(result['authority'], 'STAGING_ONLY_NO_TRAINING')

    def test_revoked_target_never_staged(self):
        self.s.revoked.add('e3')
        self.assertEqual([x['event_id'] for x in self._run_rows()], ['e2'])

    def test_revoked_context_never_exported(self):
        self.s.revoked.add('e1')
        self.assertEqual(self._run_rows(), [])

    def test_duplicate_digest_event_id_cannot_reuse_verified_target(self):
        # Independent adversarial review: a later stale digest row must not
        # borrow the earlier row's verified event_id as its own target.
        self.s.entries['A'][1]['event_id'] = 'e1'
        self.assertEqual(self._run_rows(), [])

    def test_stale_assistant_id_refused(self):
        self.s.entries['A'][0]['msg'] = 999
        self.assertEqual(self._run_rows(), [])

    def test_digest_mismatch_refused(self):
        self.s.entries['A'][0]['answer'] = 'tampered cached answer'
        self.assertEqual(self._run_rows(), [])

    def test_missing_assistant_and_nonfinal_refused(self):
        self.s.records['A'] = [r for r in self.s.records['A'] if r['event_id'] != 'e1' or r['role'] != 'assistant']
        self.assertEqual(self._run_rows(), [])
        self.s.records['A'][1]['status'] = 'DRAFT'
        self.assertEqual(self._run_rows(), [])

    def test_non_generated_target_refused(self):
        self.s.records['A'][-1]['metadata'] = '{"model_generated": "yes"}'
        self.assertEqual([x['event_id'] for x in self._run_rows()], ['e2'])

    def test_invalid_metadata_fails_closed(self):
        self.s.records['A'][3]['metadata'] = '{not-json'
        self.assertEqual([x['event_id'] for x in self._run_rows()], [])

    def test_session_isolation(self):
        self.s.add('B', 'f1', 8, 'B secret', 'B answer')
        self.s.add('B', 'f2', 10, 'B second', 'B answer2')
        rows = self._run_rows()
        self.assertEqual([x['session'] for x in rows], ['A', 'A', 'B'])
        self.assertNotIn('B secret', rows[0]['context'])

    def test_stale_export_replaced_with_empty_file(self):
        self.assertEqual(self.run_stage()['candidates'], 2)
        self.s.revoked.add('e1')
        self.assertEqual(self.run_stage()['candidates'], 0)
        self.assertEqual(self.read(), [])

    def test_replay_byte_deterministic(self):
        self.run_stage()
        first = (self.home / 'exports/sleep-ttt-candidates.jsonl').read_bytes()
        self.run_stage()
        self.assertEqual(first, (self.home / 'exports/sleep-ttt-candidates.jsonl').read_bytes())

    def test_history_failure_fails_closed(self):
        self.s.history_failure.add('A')
        self.assertEqual(self._run_rows(), [])

    def test_checkpoint_exception_does_not_replace_old_export(self):
        for i in range(4, 20):
            self.s.add('A', f'e{i}', i*2, f'u{i}', f'a{i}')
        self.run_stage()
        original = (self.home / 'exports/sleep-ttt-candidates.jsonl').read_bytes()
        def cancel():
            raise RuntimeError('cancelled')
        with self.assertRaises(RuntimeError):
            self.run_stage(cancel)
        self.assertEqual(original, (self.home / 'exports/sleep-ttt-candidates.jsonl').read_bytes())

    def _run_rows(self):
        self.run_stage()
        return self.read()


if __name__ == '__main__':
    unittest.main()
