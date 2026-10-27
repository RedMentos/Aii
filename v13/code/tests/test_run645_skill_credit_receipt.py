"""Run645: JEF AG4 skill outcome credit cannot be inferred from caller FINAL
without a durable non-abstaining same-event answer. SQLite, no native model.
"""
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.agi import hub, live

TRIGGER = 'summarize the fictional Alder plan'


class SkillCreditReceiptRun645(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.g = hub(self.r)
        self.g.skills.propose('alder_summary', [{'route': 'gist'}], trigger=TRIGGER)
        self.g.skills.set_stage('alder_summary', 'TRUSTED')

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def event(self):
        e = self.r.store.event(self.r.session, TRIGGER)
        self.assertEqual(live.skill_route(self.r, e, TRIGGER, 'simple', False, {}), 'gist')
        return e

    def answer(self, event, text, metadata=None):
        mid = self.r.store.message(self.r.session, event['event_id'], 'assistant', text)
        self.r.store.finish_message(mid, 'FINAL', metadata or {})

    def outcome(self, event, status='FINAL', meta=None):
        live.after_turn(self.r, event, meta or {}, status)
        skill = self.g.skills.get('alder_summary')
        return skill['uses'], skill['successes']

    def test_caller_final_without_persisted_message_is_failure(self):
        self.assertEqual(self.outcome(self.event()), (1, 0))

    def test_refusal_final_does_not_reward_skill(self):
        e = self.event()
        self.answer(e, "I don't know.")
        self.assertEqual(self.outcome(e), (1, 0))

    def test_abstaining_final_does_not_reward_skill(self):
        e = self.event()
        self.answer(e, 'Alder summary: 100 units', {'metacog_abstain': True})
        self.assertEqual(self.outcome(e), (1, 0))

    def test_reference_only_final_does_not_reward_skill(self):
        e = self.event()
        self.answer(e, 'Teacher reference', {'reference_only': True})
        self.assertEqual(self.outcome(e), (1, 0))

    def test_normal_persisted_final_still_credits_skill(self):
        e = self.event()
        self.answer(e, 'Alder plan: allocate 100 units.')
        self.assertEqual(self.outcome(e), (1, 1))

    def test_error_status_never_credits_even_with_message(self):
        e = self.event()
        self.answer(e, 'Alder plan: allocate 100 units.')
        self.assertEqual(self.outcome(e, 'ERROR'), (1, 0))


if __name__ == '__main__':
    unittest.main()
