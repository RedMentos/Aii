"""Run52 real Store/Cognition cross-turn source windows, synthetic body runners."""
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from scripts import run52_b1b2_cross_turn_native as run52
from v13.runtime import Runtime

FIXTURE = Path(__file__).resolve().parents[1] / 'docs/fixtures/run52_b1b2_cross_turn_seed479.json'
ORACLES = {'Harbor': ('A', 30), 'Willow': ('B', 15), 'Cobalt': ('NONE', None)}


class FakeBody:
    wrong = False

    def __init__(self, role):
        self.role = role
        self.last_metrics = {'status': 'FINAL'}

    def generate(self, msgs, *args, **kwargs):
        q = json.loads(msgs[1]['content'])
        text = ' '.join(s['text'] for s in q.get('source_segments', []))
        if not text:
            text = ' '.join(x if isinstance(x, str) else json.dumps(x) for x in q.get('gist_slots', []))
        project = next((n for n in ORACLES if n in text), None)
        if project is None:
            raise AssertionError('synthetic body needs project source')
        choice, remain = ORACLES[project]
        has_prior = bool(q.get('recent_source') or q.get('earlier_context'))
        summary = ('No eligible option' if choice == 'NONE' else f'Option {choice} leaves {remain} euros') if has_prior else 'Initial project rules'
        if self.wrong:
            summary = 'Cannot decide'
        quotes = []
        if q.get('quote_choices'):
            candidates = q['quote_choices']
            picked = next((x['id'] for x in candidates if 'Budget' in x['text']), candidates[0]['id'])
            quotes = [picked] if not self.wrong else []
        elif q.get('recent_source'):
            source = q['recent_source'][0]['exact_source_excerpt']
            m = re.search(r'Budget \d+ euros\.', source)
            quotes = [m.group()] if m and not self.wrong else []
        elif q.get('source_segments'):
            quotes = [q['source_segments'][0]['text'][:12]] if not self.wrong else []
        return [json.dumps({'summary': summary, 'quotes': quotes,
                            'uncertainty': 'low', 'needs_reentry': False})]


class FakeRuntime(Runtime):
    wrong = False

    def __init__(self, home):
        super().__init__(home)
        self.pool.get = lambda role: self._body(role)
        self.pool.unload = self._unload

    def _body(self, role):
        body = FakeBody(role)
        body.wrong = self.wrong
        return body

    def _unload(self):
        self.pool.release_history.append({'process_reaped': True, 'synthetic': True})


class B1B2CrossTurnTests(unittest.TestCase):
    def setUp(self):
        self.fixtures = run52.load_fixture(FIXTURE)['fixtures']

    def test_frozen_cohort_and_scoring(self):
        self.assertEqual([f['id'] for f in self.fixtures], ['Harbor', 'Willow', 'Cobalt'])
        self.assertEqual(run52.b1_signal('Option A leaves 30 euros', self.fixtures[0]['oracle']), 1)
        self.assertEqual(run52.b1_signal('Option B leaves 30 euros', self.fixtures[0]['oracle']), 0)
        self.assertEqual(run52.b1_signal('No eligible option', self.fixtures[2]['oracle']), 1)
        self.assertEqual(run52.b1_signal('No choice', self.fixtures[2]['oracle']), 0)

    def test_fixture_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'bad.json'
            p.write_bytes(FIXTURE.read_bytes() + b' ')
            with self.assertRaisesRegex(ValueError, 'RUN52_FIXTURE_SHA'):
                run52.load_fixture(p)

    def test_real_cognition_cross_turn_with_synthetic_body_only(self):
        with tempfile.TemporaryDirectory() as d, \
                patch.object(run52, 'Runtime', FakeRuntime), \
                patch.object(run52, 'installed_links', lambda *args: None):
            for f in self.fixtures:
                with self.subTest(project=f['id']):
                    row = run52.run_row(Path(d) / f['id'], Path(d), f)
                    self.assertEqual(row['status'], 'RECORDED', row.get('error'))
                    self.assertEqual(len(row['offers']), 4)
                    self.assertEqual(row['b1_signal'], 1)
                    self.assertEqual(row['b2_prior_transport'], 1)
                    self.assertTrue(row['processes_reaped'])
                    self.assertEqual(row['offers'][2]['query_packet']['context_source_refs'][0]['source_id'],
                                     row['prior_source_ref']['source_id'])
                    self.assertEqual(row['offers'][3]['query_packet']['context_source_refs'][0]['source_id'],
                                     row['prior_source_ref']['source_id'])

    def test_revoked_prior_source_not_reused_in_body_context(self):
        f = self.fixtures[0]
        with tempfile.TemporaryDirectory() as d:
            r = FakeRuntime(Path(d))
            try:
                r.cfg.update(run52.OVERRIDES)
                prior = r.store.event(r.session, f['prior'])
                for role in run52.ROLES:
                    r.cognition.offer(role, prior, 0, __import__('time').monotonic() + 30)
                current = r.store.event(r.session, f['current'])
                self.assertTrue(r.cognition.body_context('B1_DETAIL', current))
                self.assertTrue(r.cognition.body_context('B2_GIST', current))
                with r.store.tx() as db:
                    db.execute('UPDATE sources SET deleted=1 WHERE id=?', (prior['source_ref']['source_id'],))
                self.assertEqual(r.cognition.body_context('B1_DETAIL', current), [])
                self.assertEqual(r.cognition.body_context('B2_GIST', current), [])
            finally:
                r.close()

    def test_wrong_synthetic_body_preserves_negative_score(self):
        f = self.fixtures[0]
        class WrongRuntime(FakeRuntime):
            wrong = True
        with tempfile.TemporaryDirectory() as d, \
                patch.object(run52, 'Runtime', WrongRuntime), \
                patch.object(run52, 'installed_links', lambda *args: None):
            row = run52.run_row(Path(d) / 'wrong', Path(d), f)
            self.assertEqual(row['status'], 'RECORDED')
            self.assertEqual(row['b1_signal'], 0)
            self.assertEqual(row['b2_prior_transport'], 0)


if __name__ == '__main__':
    unittest.main()