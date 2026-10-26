"""Run620: operator-only persistent EN/DE answer-language control, actual SQLite Runtime."""
import json
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.operator import Operator
from v13.prompts import text as prompt


class LanguageOperatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def test_english_first_status_and_no_mutation(self):
        self.assertEqual(self.r.cfg['answer_language'], 'en')
        before = (self.home / 'config/settings.json').read_bytes()
        for command in (':language', ':language status'):
            out = json.loads(Operator(self.r).run(command))
            self.assertEqual(out['answer_language'], 'en')
            self.assertEqual(out['scope'], 'MODEL_PROMPTS_ONLY')
            self.assertFalse(out['learning_authorized'])
        self.assertEqual((self.home / 'config/settings.json').read_bytes(), before)
        self.assertIn('Answer in English', prompt(self.r.cfg, 'system'))

    def test_change_persists_across_restart_and_reverts(self):
        original = (self.r.cfg['learning_mode'], self.r.cfg['system_stage'],
                    self.r.cfg['latents_enabled'])
        out = json.loads(Operator(self.r).run(':language de'))
        self.assertTrue(out['changed'])
        self.assertEqual(out['previous_language'], 'en')
        self.assertEqual(self.r.cfg['answer_language'], 'de')
        self.assertIn('Antworte auf Deutsch', prompt(self.r.cfg, 'system'))
        self.assertIsNotNone(self.r.store.one(
            "SELECT 1 FROM telemetry WHERE kind='answer_language_change'"))
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.assertEqual(self.r.cfg['answer_language'], 'de')
        self.assertEqual(json.loads(Operator(self.r).run(':language'))['answer_language'], 'de')
        out = json.loads(Operator(self.r).run(':language en'))
        self.assertTrue(out['changed'])
        self.assertEqual(self.r.cfg['answer_language'], 'en')
        self.assertEqual((self.r.cfg['learning_mode'], self.r.cfg['system_stage'],
                          self.r.cfg['latents_enabled']), original)

    def test_invalid_and_nonlocal_commands_leave_config_unchanged(self):
        original = (self.home / 'config/settings.json').read_bytes()
        for command in (':language fr', ':language de extra',
                        ':language status extra', ':language --help'):
            with self.subTest(command=command), self.assertRaises(ValueError):
                Operator(self.r).run(command)
        with self.assertRaises(ValueError):
            Operator(self.r).run(':language de', origin='NONLOCAL')
        self.assertEqual((self.home / 'config/settings.json').read_bytes(), original)

    def test_busy_turn_refuses_change_without_persistence(self):
        original = (self.home / 'config/settings.json').read_bytes()
        with self.r.lock:
            self.r.current = 'turn'
            try:
                with self.assertRaises(ValueError):
                    Operator(self.r).run(':language de')
            finally:
                self.r.current = None
        self.assertEqual((self.home / 'config/settings.json').read_bytes(), original)
        self.assertEqual(self.r.cfg['answer_language'], 'en')

    def test_same_language_is_idempotent(self):
        original = (self.home / 'config/settings.json').read_bytes()
        out = json.loads(Operator(self.r).run(':language en'))
        self.assertFalse(out['changed'])
        self.assertEqual((self.home / 'config/settings.json').read_bytes(), original)
        self.assertIsNone(self.r.store.one(
            "SELECT 1 FROM telemetry WHERE kind='answer_language_change'"))


if __name__ == '__main__':
    unittest.main()
