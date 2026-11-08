"""AG2/AG4: a technical FINAL is not a semantic success label."""
import copy
import unittest
from unittest.mock import patch
from v13.agi import live
from v13.agi.skills import SkillLibrary


class MemoryStore:
    def __init__(self):
        self.values = {}
        self.logs = []
    def state(self, key, default=None):
        val, ver = self.values.get(key, (default, None))
        return copy.deepcopy(val), ver
    def set_state(self, key, value, expected=None):
        old, ver = self.values.get(key, (None, None))
        if expected != ver:
            raise ValueError("CAS conflict")
        self.values[key] = (copy.deepcopy(value), (ver or 0) + 1)
    def log(self, kind, event_id, payload):
        self.logs.append((kind, event_id, payload))


class LiveSkillOutcomeTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        self.skills = SkillLibrary(self.store)
        self.skills.propose('quick_route', [{'route': 'simple'}], trigger='hello')
        self.skills.set_stage('quick_route', 'TRUSTED')
        live._save(self.store, 'e1', skill='quick_route')
    def test_technical_final_does_not_train_skill(self):
        runtime = type('Runtime', (), {})()
        runtime.store = self.store
        fake = type('Hub', (), {'grounding': type('Grounding', (), {})(), 'skills': self.skills})()
        with patch.object(live, 'hub', return_value=fake), patch.object(live, 'sync_slots'), patch.object(live, 'goal_turn'):
            with patch('v13.maturity.turn_feed'):
                live.after_turn(runtime, {'event_id': 'e1'}, {}, 'FINAL')
        self.assertEqual(self.skills.get('quick_route')['uses'], 0)
        self.assertEqual(live._load(self.store, 'e1')['skill_outcome'], 'AWAITING_HUMAN')
    def test_human_rating_once_survives_restart(self):
        self.assertTrue(live._human_skill_outcome(self.store, 'e1', True, 'rating:e1'))
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
        self.assertEqual(self.skills.record_human('quick_route', 'e1', True), 'RECORDED')
        self.assertFalse(live._human_skill_outcome(self.store, 'e1', True, 'rating:e1'))
        self.assertEqual(self.skills.get('quick_route')['uses'], 1)
    def test_cross_skill_rebinding_refused(self):
        self.skills.propose('other_route', [{'route': 'gist'}], trigger='other')
        self.skills.record_human('quick_route', 'e1', True)
        with self.assertRaises(ValueError):
            self.skills.record_human('other_route', 'e1', True)
    def test_fact_correction_retracts_skill_credit(self):
        self.skills.record_human('quick_route', 'e1', True)
        live._save(self.store, 'e1', skill_human_credit=True)
        with patch('v13.agi.metacog.Metacognition'):
            live.on_feedback(self.store, 'e1', 'fact', 'wrong')
        self.assertEqual(self.skills.get('quick_route')['successes'], 0)

    def test_rating_without_metacog_confidence_still_credits_skill(self):
        with patch('v13.agi.metacog.Metacognition'):
            self.assertTrue(live.on_rating(self.store, 'e1', 8))
        self.assertEqual(self.skills.get('quick_route')['uses'], 1)
    def test_neutral_rating_never_credits_skill(self):
        self.assertIsNone(live.on_rating(self.store, 'e1', 5))
        self.assertEqual(self.skills.get('quick_route')['uses'], 0)


if __name__ == '__main__':
    unittest.main()
