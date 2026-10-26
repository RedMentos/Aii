"""Run448: English-first model prompt language can be selected by the human only.

Model-free, real Runtime/Operator/SQLite/config path. Language selection is NOT
evidence of learning German and does not alter Age, training, or model weights.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.config import DEFAULTS
from v13.operator import Operator
from v13.prompts import text
from v13.runtime import Runtime


class OperatorLanguageLifecycle(unittest.TestCase):
    def test_explicit_switch_persists_across_restart_without_learning(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            r = Runtime(home)
            try:
                op = Operator(r)
                before = r.store.generation_id
                self.assertEqual(DEFAULTS['answer_language'], 'en')
                self.assertEqual(json.loads(op.run(':language')),
                                 {'answer_language': 'en', 'default': 'en',
                                  'scope': 'model_prompts', 'training_effect': 'none'})
                self.assertIn('Answer in English', text(r.cfg, 'system'))
                self.assertIn('answer_language = de', op.run(':language de'))
                self.assertEqual(json.loads(op.run(':language status'))['answer_language'], 'de')
                self.assertIn('auf Deutsch', text(r.cfg, 'system'))
                self.assertEqual(r.store.generation_id, before)
                self.assertIn(':language', op.run(':befehle language'))
                self.assertEqual(json.loads((home / 'config/settings.json').read_text())['answer_language'], 'de')
            finally:
                r.close()
            r = Runtime(home)
            try:
                op = Operator(r)
                self.assertEqual(json.loads(op.run(':language'))['answer_language'], 'de')
                self.assertIn('auf Deutsch', text(r.cfg, 'system'))
                self.assertIn('answer_language = en', op.run(':language en'))
                self.assertIn('Answer in English', text(r.cfg, 'system'))
                self.assertEqual(r.store.generation_id, before)
            finally:
                r.close()

    def test_invalid_or_nonoperator_switch_is_refused_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Runtime(Path(tmp))
            try:
                op = Operator(r)
                settings = (r.home / 'config/settings.json')
                original = settings.read_bytes()
                for cmd in (':language fr', ':language de extra', ':language STATUS extra'):
                    with self.subTest(cmd=cmd), self.assertRaises(ValueError):
                        op.run(cmd)
                    self.assertEqual(settings.read_bytes(), original)
                with self.assertRaises(ValueError):
                    op.run(':language de', origin='MODEL')
                self.assertEqual(settings.read_bytes(), original)
                with patch.object(r, 'require_idle', side_effect=RuntimeError('busy')):
                    with self.assertRaisesRegex(RuntimeError, 'busy'):
                        op.run(':language de')
                self.assertEqual(settings.read_bytes(), original)
                self.assertEqual(r.cfg['answer_language'], 'en')
            finally:
                r.close()


if __name__ == '__main__':
    unittest.main()
