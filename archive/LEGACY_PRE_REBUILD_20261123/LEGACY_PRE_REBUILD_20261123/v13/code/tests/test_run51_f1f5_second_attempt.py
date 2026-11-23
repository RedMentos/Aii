"""Run51 real Store F1/F5 correction and clearly synthetic C3 receiver tests."""
import json
from pathlib import Path
import re
import tempfile
import threading
import unittest
from unittest.mock import patch

from scripts import run51_f1f5_second_attempt_native as run51
from v13.config import DEFAULTS, initialize
from v13.memory import Memory
from v13.source_consumer import verified_recall_messages, render_messages
from v13.store import Store

FIXTURE = Path(__file__).resolve().parents[1] / 'docs/fixtures/run51_f1f5_second_attempt_seed467.json'


class FakeRunner:
    def __init__(self, wrong=False):
        self.wrong = wrong
        self.last_metrics = {'status': 'FINAL'}

    def generate(self, msgs, cancel, deadline, tokens, schema, seed):
        m = re.search(r'Verified user correction for this topic: Project (\w+) budget = (\d+) Euro', msgs[0]['content'])
        if not m:
            raise AssertionError('synthetic receiver needs source-bound correction')
        name, amount = m.groups()
        return [f'Project {name} budget is {999 if self.wrong else amount} Euro.']


class FakePool:
    def __init__(self, wrong=False):
        self.runner = FakeRunner(wrong)
        self.release_history = []

    def get(self, role):
        if role != 'C3_LANGUAGE':
            raise AssertionError('only synthetic C3 allowed')
        return self.runner

    def unload(self):
        if not self.release_history:
            self.release_history.append({'process_reaped': True, 'synthetic': True})


class FakeRuntime:
    wrong = False

    def __init__(self, home):
        self.store = Store(home)
        self.session = self.store.new_session()
        self.cancel_event = threading.Event()
        self.pool = FakePool(self.wrong)

    def close(self):
        self.pool.unload()
        self.store.close()


class F1F5SecondAttemptTests(unittest.TestCase):
    def setUp(self):
        self.fixtures = run51.load_fixture(FIXTURE)['fixtures']
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        initialize(self.home)
        self.store = Store(self.home)
        self.session = self.store.new_session()
        self.memory = Memory(self.store, DEFAULTS)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def correct(self, f):
        event = self.store.event(self.session, f['correction_event'])
        return self.memory.feedback(event['event_id'], 'fact', f['value'],
                                    permission='record', key=f['key'], scope='session')

    def test_frozen_cohort_and_exact_score(self):
        self.assertEqual([f['id'] for f in self.fixtures], ['Cypress', 'Lark', 'Delta'])
        self.assertEqual([f['oracle_amount'] for f in self.fixtures], [64, 27, 91])
        self.assertEqual(run51.score('Project Cypress budget is 64 Euro.', 64, 'Cypress'), 1)
        for bad in ('64.00 Euro', '64 Euro and 65 Euro', 'Project Lark budget is 64 Euro', '640 Euro', ''):
            self.assertEqual(run51.score(bad, 64, 'Cypress'), 0)

    def test_no_source_clarify_then_verified_second_attempt(self):
        f = self.fixtures[0]
        first = verified_recall_messages(DEFAULTS, f['first_query'], self.session, self.memory)
        self.assertEqual(first['decision']['status'], 'CLARIFY')
        self.assertIsNone(first['messages'])
        mid = self.correct(f)
        second = verified_recall_messages(DEFAULTS, f['followup'], self.session, self.memory)
        self.assertEqual(second['decision']['status'], 'ADMITTED')
        self.assertEqual(second['decision']['source']['value'], f['value'])
        self.assertEqual(second['decision']['source']['memory_id'], mid)
        self.assertIn(f['value'], second['messages'][0]['content'])
        self.assertNotIn(f['value'], second['messages'][1]['content'])
        self.assertEqual(self.store.one('SELECT permission FROM feedback WHERE event_id=?',
                         (self.store.one('SELECT event_id FROM memories WHERE id=?', (mid,))['event_id'],))['permission'], 'record')

    def test_restart_recall_then_forget_blocks_prompt(self):
        f = self.fixtures[0]
        mid = self.correct(f)
        self.store.close()
        self.store = Store(self.home)
        self.memory = Memory(self.store, DEFAULTS)
        self.assertEqual(verified_recall_messages(DEFAULTS, f['followup'], self.session, self.memory)['decision']['status'], 'ADMITTED')
        self.memory.forget(mid)
        denied = verified_recall_messages(DEFAULTS, f['followup'], self.session, self.memory)
        self.assertEqual(denied['decision']['status'], 'CLARIFY')
        self.assertIsNone(denied['messages'])

    def test_foreign_session_project_and_forged_seal_rejected(self):
        f = self.fixtures[0]
        self.correct(f)
        foreign = self.store.new_session('foreign')
        self.assertIsNone(verified_recall_messages(DEFAULTS, f['followup'], foreign, self.memory)['messages'])
        self.assertIsNone(verified_recall_messages(DEFAULTS, self.fixtures[1]['followup'], self.session, self.memory)['messages'])
        admitted = verified_recall_messages(DEFAULTS, f['followup'], self.session, self.memory)['decision']
        admitted['_render_seal'] = 'forged'
        with self.assertRaises(ValueError):
            render_messages(DEFAULTS, f['followup'], admitted, memory=self.memory, session=self.session)

    def test_conflicting_active_aliases_and_revoked_source_block_prompt(self):
        f = self.fixtures[0]
        mid = self.correct(f)
        event = self.store.event(self.session, 'Correction: Project Cypress budgets is 73 Euro.')
        self.memory.feedback(event['event_id'], 'fact', '73 Euro', permission='record',
                             key='Project Cypress budgets', scope='session')
        refused = verified_recall_messages(DEFAULTS, f['followup'], self.session, self.memory)
        self.assertEqual(refused['decision']['status'], 'CLARIFY')
        self.assertIsNone(refused['messages'])
        with self.store.tx() as db:
            db.execute('UPDATE sources SET deleted=1 WHERE id=(SELECT source_id FROM memories WHERE id=?)', (mid,))
        refused = verified_recall_messages(DEFAULTS, f['followup'], self.session, self.memory)
        self.assertEqual(refused['decision']['status'], 'CLARIFY')
        self.assertIsNone(refused['messages'])

    def test_three_real_store_rows_with_synthetic_receiver_only(self):
        with tempfile.TemporaryDirectory() as d, \
                patch.object(run51, 'Runtime', FakeRuntime), \
                patch.object(run51, 'installed_links', lambda *args: None):
            for f in self.fixtures:
                with self.subTest(project=f['id']):
                    row = run51.run_row(Path(d) / f['id'], Path(d), f)
                    self.assertEqual(row['status'], 'RECORDED')
                    self.assertEqual(row['baseline_decision'], 'CLARIFY')
                    self.assertEqual(row['second_decision'], 'ADMITTED')
                    self.assertEqual(row['score']['correct'], 1)
                    self.assertEqual(row['native_model_calls'], 1)
                    self.assertEqual(row['baseline_model_calls'], 0)
                    self.assertTrue(row['processes_reaped'])
                    self.assertEqual(len(row['f1f5_packets']), 2)

    def test_wrong_synthetic_receiver_keeps_scientific_red(self):
        f = self.fixtures[0]
        class WrongRuntime(FakeRuntime):
            wrong = True
        with tempfile.TemporaryDirectory() as d, \
                patch.object(run51, 'Runtime', WrongRuntime), \
                patch.object(run51, 'installed_links', lambda *args: None):
            row = run51.run_row(Path(d) / 'bad', Path(d), f)
            self.assertEqual(row['status'], 'RECORDED')
            self.assertEqual(row['score']['correct'], 0)


if __name__ == '__main__':
    unittest.main()