"""AG2/AG4: a technical FINAL is not a semantic success label."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from v13.agi import live
from v13.agi.skills import SkillLibrary
from v13.runtime import Runtime


class LiveSkillOutcomeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = Runtime(Path(self.tmp.name))
        self.store = self.runtime.store
        self.skills = SkillLibrary(self.store)
        self.skills.propose('quick_route', [{'route': 'simple'}], trigger='hello')
        self.skills.set_stage('quick_route', 'TRUSTED')
        self.binding = self.skills.human_binding('quick_route')
        live._save(self.store, 'e1', skill='quick_route', skill_binding=self.binding)
    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()
    def test_technical_final_does_not_train_skill(self):
        runtime = type('Runtime', (), {})()
        runtime.store = self.store
        fake = type('Hub', (), {'grounding': type('Grounding', (), {})(), 'skills': self.skills})()
        with patch.object(live, 'hub', return_value=fake), patch.object(live, 'sync_slots'), patch.object(live, 'goal_turn'):
            with patch('v13.agi.maturity.turn_feed'):
                live.after_turn(runtime, {'event_id': 'e1'}, {}, 'FINAL')
        self.assertEqual(self.skills.get('quick_route')['uses'], 0)
        self.assertEqual(live._load(self.store, 'e1')['skill_outcome'], 'AWAITING_HUMAN')
    def test_human_rating_once_survives_restart(self):
        self.assertTrue(live._human_skill_outcome(self.store, 'e1', True, 'rating:e1'))
        self.runtime.close()
        self.runtime = Runtime(Path(self.tmp.name))
        self.store = self.runtime.store
        self.skills = SkillLibrary(self.store)
        self.assertFalse(live._human_skill_outcome(self.store, 'e1', True, 'rating:e1'))
        self.assertEqual(SkillLibrary(self.store).get('quick_route')['uses'], 1)
        self.assertEqual(SkillLibrary(self.store).get('quick_route')['successes'], 1)
    def test_correction_does_not_double_credit(self):
        live._human_skill_outcome(self.store, 'e1', True, 'rating:e1')
        self.assertTrue(live._human_skill_outcome(self.store, 'e1', False, 'rating:e1'))
        self.assertEqual(self.skills.get('quick_route')['uses'], 1)
        self.assertEqual(self.skills.get('quick_route')['successes'], 0)
        self.assertTrue(live._load(self.store, 'e1')['skill_disputed'])
    def test_recovery_after_ledger_commit_before_marker(self):
        self.assertEqual(self.skills.record_human('quick_route', 'e1', True, self.binding), 'RECORDED')
        self.assertFalse(live._human_skill_outcome(self.store, 'e1', True, 'rating:e1'))
        self.assertEqual(self.skills.get('quick_route')['uses'], 1)
    def test_cross_skill_rebinding_refused(self):
        self.skills.propose('other_route', [{'route': 'gist'}], trigger='other')
        self.skills.record_human('quick_route', 'e1', True, self.binding)
        with self.assertRaises(ValueError):
            self.skills.record_human('other_route', 'e1', True, self.skills.human_binding('other_route'))
    def test_fact_correction_retracts_skill_credit(self):
        self.skills.record_human('quick_route', 'e1', True, self.binding)
        live._save(self.store, 'e1', skill_human_credit=True)
        with patch('v13.agi.metacog.Metacognition'):
            live.on_feedback(self.store, 'e1', 'fact', 'wrong')
        self.assertEqual(self.skills.get('quick_route')['successes'], 0)

    def test_rating_without_metacog_confidence_still_credits_skill(self):
        with patch('v13.agi.metacog.Metacognition'):
            self.assertTrue(live.on_rating(self.store, 'e1', 8, origin='EXPLICIT_NOTE'))
        self.assertEqual(self.skills.get('quick_route')['uses'], 1)
    def test_metacog_duplicate_rating_receipt(self):
        from v13.agi.metacog import Metacognition
        live._save(self.store, 'e1', answer_confidence=0.8)
        live.on_rating(self.store, 'e1', 8, origin='EXPLICIT_NOTE')
        live.on_rating(self.store, 'e1', 8, origin='EXPLICIT_NOTE')
        self.assertEqual(Metacognition(self.store).report('answer')['components']['answer']['n'], 1)
        self.assertEqual(self.skills.get('quick_route')['uses'], 1)

    def test_neutral_rating_never_credits_skill(self):
        self.assertIsNone(live.on_rating(self.store, 'e1', 5))
        self.assertEqual(self.skills.get('quick_route')['uses'], 0)


if __name__ == '__main__':
    unittest.main()
