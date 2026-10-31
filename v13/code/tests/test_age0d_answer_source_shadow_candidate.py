"""Run113 preregistered Age0d answer-sees-source read-only SHADOW tests."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from v13.runtime import Runtime
from v13.age0d_answer_source_shadow_candidate import check

FIXTURE = Path(__file__).resolve().parents[1] / 'docs/fixtures/RUN113_AGE0D_ANSWER_SOURCE_SEED941.json'
FIXTURE_SHA = '553a068e38c15a10c8b477ac18c14bf45f437da09fb58a3006168616552e2d43'


class Age0DAnswerSeesSource(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.r = Runtime(Path(self.tmp.name))
        self.addCleanup(self.r.close)

    def event(self, text):
        return self.r.store.event(self.r.session, text)

    def counts(self):
        return (
            self.r.store.one('SELECT COUNT(*) AS n FROM messages')['n'],
            self.r.store.one('SELECT COUNT(*) AS n FROM actions')['n'],
            self.r.store.one('SELECT COUNT(*) AS n FROM packets')['n'],
        )

    def test_exact_frozen_ten_case_cohort_no_false_alarm(self):
        raw = FIXTURE.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), FIXTURE_SHA)
        data = json.loads(raw)
        self.assertEqual(data['seed'], 941)
        self.assertEqual(len(data['rows']), 10)
        seen = {}
        for row in data['rows']:
            e = self.event(row['source'])
            before = self.counts()
            result = check(self.r, e['event_id'], e['source_ref'],
                           row['answer'], operator_opt_in=True)
            self.assertEqual(result['verdict'], row['expected'], row['id'])
            self.assertEqual(self.counts(), before)
            self.assertNotIn(row['source'], str(result))
            self.assertNotIn(row['answer'], str(result))
            self.assertFalse(result['native_model_called'])
            self.assertEqual(result['delivery_authority'], 0)
            self.assertEqual(result['learning_authority'], 0)
            self.assertEqual(result['jepa_weight'], 0)
            seen[result['verdict']] = seen.get(result['verdict'], 0) + 1
        self.assertEqual(seen, {'NO_SIGNAL': 4, 'CONTRADICTION': 4, 'ABSTAIN': 2})

    def test_default_off_does_not_even_read_source_or_event(self):
        e = self.event('Project Vela budget: 615 Euro.')
        with patch.object(self.r.store, 'one', side_effect=AssertionError('unexpected read')):
            result = check(self.r, e['event_id'], e['source_ref'],
                           'The budget for Project Vela is 651 Euro.')
        self.assertEqual(result['verdict'], 'OFF')
        self.assertIsNone(result['source_ref_sha256'])

    def test_deleted_source_fails_closed(self):
        e = self.event('Project Vela budget: 615 Euro.')
        with self.r.store.tx() as db:
            db.execute('UPDATE sources SET deleted=1 WHERE id=?',
                       (e['source_ref']['source_id'],))
        result = check(self.r, e['event_id'], e['source_ref'],
                       'The budget for Project Vela is 651 Euro.',
                       operator_opt_in=True)
        self.assertEqual(result['verdict'], 'SOURCE_RED')

    def test_cross_event_source_ref_refused(self):
        first = self.event('Project Vela budget: 615 Euro.')
        second = self.event('Project Rhea budget: 240 Euro.')
        result = check(self.r, second['event_id'], first['source_ref'],
                       'The budget for Project Vela is 651 Euro.',
                       operator_opt_in=True)
        self.assertEqual(result['verdict'], 'SOURCE_RED')

    def test_tampered_source_span_refused(self):
        e = self.event('Project Vela budget: 615 Euro.')
        ref = dict(e['source_ref'], char_end=e['source_ref']['char_end'] - 1)
        result = check(self.r, e['event_id'], ref,
                       'The budget for Project Vela is 651 Euro.',
                       operator_opt_in=True)
        self.assertEqual(result['verdict'], 'SOURCE_RED')

    def test_wrong_project_does_not_flag(self):
        e = self.event('Project Vela budget: 615 Euro.')
        result = check(self.r, e['event_id'], e['source_ref'],
                       'The budget for Project Rhea is 651 Euro.',
                       operator_opt_in=True)
        self.assertEqual(result['verdict'], 'ABSTAIN')

    def test_unsupported_json_and_unrelated_numbers_abstain(self):
        e = self.event('Project Vela budget: 615 Euro.')
        for answer in ('{"budget":615}', 'I have 651 suggestions.',
                       'Budget maybe 651', 'The answer is 615.'):
            result = check(self.r, e['event_id'], e['source_ref'],
                           answer, operator_opt_in=True)
            self.assertEqual(result['verdict'], 'ABSTAIN', answer)

    def test_answer_missing_or_oversized_refused(self):
        e = self.event('Project Vela budget: 615 Euro.')
        for answer in ('', 'a' * 4097, None):
            result = check(self.r, e['event_id'], e['source_ref'],
                           answer, operator_opt_in=True)
            self.assertEqual(result['verdict'], 'SOURCE_RED')


if __name__ == '__main__':
    unittest.main()
