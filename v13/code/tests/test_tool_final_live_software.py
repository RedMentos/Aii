"""Actual Runtime.submit software integration for eligibility final output provenance.

Synthetic, explicitly approved READ_LOCAL tool seam; no native model or Redmi.
"""
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock

from v13.runtime import Runtime
from v13.agi import hub, eligibility
from v13.toolstep import ToolStep

OPTIONS = ('Option A: cost 45 euros, duration 7 days, local true. '
           'Option B: cost 55 euros, duration 4 days, local false. '
           'Which option should I choose?')
UNKNOWN = 'Project Orion. '+OPTIONS
NONE = ('Project Orion. Budget 20 euros. Deadline 3 days. '
        'Local-only requirement: true. '+OPTIONS)
CHOOSE_A = ('Project Orion. Budget 61 euros. Deadline 8 days. '
            'Local-only requirement: false. '+OPTIONS)


class SyntheticC3:
    role = 'C3_LANGUAGE'
    memory = None

    def __init__(self):
        self.calls = 0
        self.last_metrics = {'stale_native_sentinel': 'DO_NOT_CREDIT'}

    def generate(self, messages, cancel, deadline, *args, **kwargs):
        self.calls += 1
        yield ' Synthetic native-continuation stub.'


class RuntimeToolFinalSoftware(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.r.cfg.update(eligibility_reader='fixed', tool_answer_first=True,
                          observer_mode='off', tool_conflict_policy='log')
        self.r._route = Mock(return_value=('simple', {'source': 'TEST_ROUTE_SEAM'}))
        self.runner = SyntheticC3()
        self.r.pool.get = Mock(return_value=self.runner)
        self.r.learner.output_delta = Mock(return_value=None)
        self.tools = hub(self.r).tools
        self.tools.enable('eligibility')

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def _turn(self, prompt):
        self.r.submit(prompt)
        until = time.monotonic()+20
        while not self.r.idle() and time.monotonic()<until:
            time.sleep(.01)
        self.assertTrue(self.r.idle(), 'actual worker failed to settle')
        row = self.r.last_answer()
        self.assertIsNotNone(row)
        self.assertEqual(row['status'], 'FINAL', row)
        stored = self.r.store.one('SELECT metadata FROM messages WHERE id=?', (row['id'],))
        meta = json.loads(stored['metadata'])
        broker = self.r.store.one(
            "SELECT payload FROM packets WHERE kind='OutputBrokerDecision' AND event_id=? ORDER BY rowid DESC LIMIT 1",
            (row['event_id'],))
        self.assertIsNotNone(broker, 'actual C7 output decision must persist')
        return row, meta, json.loads(broker['payload'])

    def test_age_zero_unpatched_policy_never_auto_executes(self):
        event = self.r.store.event(self.r.session, UNKNOWN)
        plan = ToolStep(self.r).plan(event, UNKNOWN)
        self.assertIsNotNone(plan)
        self.assertNotEqual(plan['status'], 'APPROVED')
        self.assertEqual(self.runner.calls, 0)
        self.assertIsNone(self.r.store.one(
            "SELECT id FROM packets WHERE kind='OutputBrokerDecision' AND event_id=?",
            (event['event_id'],)))

    def test_unknown_and_none_use_exact_tool_text_without_native_generation(self):
        # Explicitly synthetic test authorization: production Age-0 rights remain unchanged.
        self.tools._policy = Mock(return_value=('APPROVED', 'TEST_ONLY_AUTHORIZATION', []))
        for text, expected_action in ((UNKNOWN, 'UNKNOWN'), (NONE, 'NONE')):
            with self.subTest(action=expected_action):
                row, meta, broker = self._turn(text)
                calls = self.r.store.rows(
                    "SELECT payload FROM packets WHERE kind='ToolResult' AND event_id=?",
                    (row['event_id'],))
                self.assertEqual(self.runner.calls, 0, 'fixed tool final must not invoke native answer')
                self.assertIs(meta.get('model_generated'), False)
                self.assertIs(meta.get('native_answer_skipped'), True)
                self.assertEqual(meta.get('output_authority'), 'ELIGIBILITY_TOOL_FINAL')
                self.assertNotIn('stale_native_sentinel', json.dumps(meta))
                self.assertEqual(broker['authority'], 'ELIGIBILITY_TOOL_FINAL')
                self.assertEqual(broker['conflicts'], [])
                self.assertEqual(broker['egress_type'], 'TEXT_REPORT')
                self.assertTrue(row['text'])
                self.assertIn(expected_action, ('UNKNOWN', 'NONE'))
                self.assertEqual(meta.get('tool_answer_first'), 'FINAL')

    def test_a_choice_still_uses_native_continuation_stub(self):
        self.tools._policy = Mock(return_value=('APPROVED', 'TEST_ONLY_AUTHORIZATION', []))
        row, meta, broker = self._turn(CHOOSE_A)
        self.assertEqual(self.runner.calls, 1)
        self.assertTrue(meta['model_generated'])
        self.assertEqual(meta.get('tool_answer_first'), 'LEAD')
        self.assertIn('Choose Option A.', row['text'])
        self.assertIn('Synthetic native-continuation stub.', row['text'])
        self.assertEqual(broker['authority'], 'MODEL_ANSWER')


if __name__ == '__main__':
    unittest.main()
