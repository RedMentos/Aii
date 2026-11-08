"""Real-store counterexamples for the parallel AG4 human-outcome candidate."""
from pathlib import Path
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from v13 import inputs
from v13.agi import live
from v13.agi.skills import SkillLibrary
from v13.runtime import Runtime


class HumanSkillOutcomeReview(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = Runtime(Path(self.tmp.name))
        self.store = self.runtime.store
        self.skills = SkillLibrary(self.store)
        self.skills.propose('quick_route', [{'route': 'simple'}], trigger='hello')

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def event(self):
        event = self.store.event(self.runtime.session, 'hello')
        eid = event['event_id']
        live._save(self.store, eid, skill='quick_route', skill_binding=self.skills.human_binding('quick_route'))
        message = self.store.message(self.runtime.session, eid, 'assistant', 'synthetic answer')
        self.store.finish_message(message, 'FINAL', {})
        return eid

    def test_implicit_chat_is_not_explicit_skill_credit(self):
        eid = self.event()
        inputs.record_rating(self.store, eid, 8, 'IMPLICIT_CHAT')
        self.assertEqual(self.skills.get('quick_route')['uses'], 0)
        inputs.record_rating(self.store, eid, 2, 'EXPLICIT_NOTE')
        inputs.record_rating(self.store, eid, 8, 'IMPLICIT_CHAT')
        sk = self.skills.get('quick_route')
        self.assertEqual((sk['uses'], sk['successes']), (1, 0))

    def test_correction_after_reopen_cannot_make_success_count_negative(self):
        self.skills.set_stage('quick_route', 'TRUSTED')
        binding = self.skills.human_binding('quick_route')
        self.skills.record_human('quick_route', 'e1', True, binding)
        self.skills.reopen('quick_route', 'route_correction')
        self.skills.record_human('quick_route', 'e1', False, binding)
        self.assertEqual(self.skills.get('quick_route')['successes'], 0)

    def test_correction_after_promotion_cannot_debit_new_stage(self):
        binding = self.skills.human_binding('quick_route')
        self.skills.record_human('quick_route', 'e1', True, binding)
        self.skills.record('quick_route', True, parity=1.)
        self.skills.record('quick_route', True, parity=1.)
        self.assertEqual(self.skills.get('quick_route')['stage'], 'SHADOW')
        self.skills.record_human('quick_route', 'e1', False, binding)
        self.assertEqual(self.skills.get('quick_route')['successes'], 0)

    def test_old_receipt_does_not_change_recreated_skill(self):
        binding = self.skills.human_binding('quick_route')
        self.skills.record_human('quick_route', 'e1', True, binding)
        self.skills.set_stage('quick_route', 'RETIRED')
        self.skills.propose('quick_route', [{'route': 'gist'}], trigger='hello')
        self.assertNotEqual(binding['instance'], self.skills.human_binding('quick_route')['instance'])
        with self.assertRaises(ValueError):
            self.skills.record_human('quick_route', 'e1', False, binding)
        sk = self.skills.get('quick_route')
        self.assertEqual((sk['uses'], sk['successes']), (0, 0))

    def test_first_late_rating_does_not_credit_new_counter_epoch(self):
        self.skills.set_stage('quick_route', 'TRUSTED')
        binding = self.skills.human_binding('quick_route')
        self.skills.reopen('quick_route', 'route_correction')
        self.skills.record_human('quick_route', 'e1', True, binding)
        sk = self.skills.get('quick_route')
        self.assertEqual((sk['uses'], sk['successes']), (1, 0))

    def test_missing_turn_binding_rejects_skill_credit(self):
        eid = self.event()
        live._save(self.store, eid, skill_binding=None)
        inputs.record_rating(self.store, eid, 8, 'EXPLICIT_NOTE')
        self.assertEqual(self.skills.get('quick_route')['uses'], 0)
        self.assertEqual(inputs.ratings(self.store)[-1]['score'], 8)

    def test_legacy_receipt_without_binding_requires_migration(self):
        binding = self.skills.human_binding('quick_route')
        def old_state(st):
            st['human_outcomes'] = {'e1': {'skill': 'quick_route', 'success': True}}
            st['skills']['quick_route']['uses'] = 1
            st['skills']['quick_route']['successes'] = 1
        self.skills.box.mutate(old_state)
        with self.assertRaises(ValueError):
            self.skills.record_human('quick_route', 'e1', False, binding)
        self.assertEqual(self.skills.get('quick_route')['successes'], 1)

    def test_automatic_skill_route_saves_binding_before_rating(self):
        from v13 import skilllive
        self.skills.set_stage('quick_route', 'TRUSTED')
        event = self.store.event(self.runtime.session, 'hello')
        eid = event['event_id']
        self.assertEqual(skilllive.automatic(self.runtime, event, 'hello', {})[0], 'simple')
        message = self.store.message(self.runtime.session, eid, 'assistant', 'synthetic answer')
        self.store.finish_message(message, 'FINAL', {})
        inputs.record_rating(self.store, eid, 8, 'EXPLICIT_NOTE')
        self.assertEqual((self.skills.get('quick_route')['uses'],
                          self.skills.get('quick_route')['successes']), (1, 1))

    def test_runtime_turn_feedback_and_restart(self):
        self.skills.set_stage('quick_route', 'TRUSTED')
        self.runtime.sleep.cycle.set_policy('enabled', 'off')
        self.runtime.pool.get = Mock(return_value=SimpleNamespace(
            role='C3_LANGUAGE', last_metrics={}, generate=lambda *a, **kw: iter(['synthetic answer'])))
        self.runtime.learner.output_delta = Mock(return_value=None)
        eid = self.runtime.submit('hello, can you explain this?')
        deadline = time.monotonic() + 10
        while not self.runtime.idle() and time.monotonic() < deadline:
            time.sleep(.005)
        answer = self.runtime.last_answer()
        self.assertEqual((answer['event_id'], answer['status']), (eid, 'FINAL'))
        self.assertIn('skill_binding', live._load(self.store, eid))
        self.assertEqual(self.skills.get('quick_route')['uses'], 0)
        inputs.record_rating(self.store, eid, 8, 'EXPLICIT_NOTE')
        inputs.record_rating(self.store, eid, 8, 'EXPLICIT_NOTE')
        self.runtime.close()
        self.runtime = Runtime(Path(self.tmp.name))
        self.store = self.runtime.store
        self.skills = SkillLibrary(self.store)
        self.assertEqual((self.skills.get('quick_route')['uses'],
                          self.skills.get('quick_route')['successes']), (1, 1))
        inputs.record_rating(self.store, eid, 2, 'EXPLICIT_NOTE')
        self.assertEqual((self.skills.get('quick_route')['uses'],
                          self.skills.get('quick_route')['successes']), (1, 0))

    def test_metacog_failure_does_not_skip_skill_feedback(self):
        eid = self.event()
        live._save(self.store, eid, answer_confidence=.8)
        with patch('v13.agi.metacog.Metacognition.record_batch', side_effect=ValueError('invalid')):
            inputs.record_rating(self.store, eid, 8, 'EXPLICIT_NOTE')
        self.assertEqual(self.skills.get('quick_route')['uses'], 1)

    def test_metacog_failure_does_not_skip_fact_correction(self):
        eid = self.event()
        live._save(self.store, eid, answer_confidence=.8)
        inputs.record_rating(self.store, eid, 8, 'EXPLICIT_NOTE')
        with patch('v13.agi.metacog.Metacognition.record', side_effect=ValueError('invalid')):
            self.runtime.memory.feedback(eid, 'fact', 'corrected fact')
        sk = self.skills.get('quick_route')
        self.assertEqual((sk['uses'], sk['successes']), (1, 0))


if __name__ == '__main__':
    unittest.main()
