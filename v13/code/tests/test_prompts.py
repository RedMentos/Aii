import unittest
from v13 import prompts
from v13.config import DEFAULTS,validate

class EnglishFirstPrompts(unittest.TestCase):
    def test_default_is_english_and_german_stays_selectable(self):
        self.assertEqual(DEFAULTS['answer_language'],'en')
        self.assertIn('Answer in English',prompts.text(DEFAULTS,'system'))
        self.assertIn('auf Deutsch',prompts.text(DEFAULTS|{'answer_language':'de'},'system'))
        with self.assertRaises(ValueError):validate(dict(DEFAULTS,answer_language='fr'))
    def test_both_languages_define_the_same_keys(self):
        self.assertEqual(set(prompts.TEXT['en']),set(prompts.TEXT['de']))
        self.assertEqual(len(prompts.TEXT['en']['probe_fixtures']),len(prompts.TEXT['de']['probe_fixtures']))
    def test_production_code_has_no_hardcoded_german_answer_instruction(self):
        from pathlib import Path
        root=Path(prompts.__file__).parent
        for name in ('runtime.py','verification.py','proofs.py','__main__.py'):
            self.assertNotIn('auf Deutsch',(root/name).read_text(),name)

class ConductAndPrivacy(unittest.TestCase):
    def test_conduct_rule_is_harm_based_and_open(self):
        for lang in ('en','de'):
            t=prompts.TEXT[lang]['conduct']
            self.assertTrue(('fiction' in t) or ('Fiktion' in t));self.assertTrue(('reason' in t) or ('Grund' in t))
    def test_telemetry_never_keeps_content_fields(self):
        from v13.store import telemetry_metrics
        kept=telemetry_metrics({'text':'geheim','output':'geheim','query':'geheim','messages':[{'content':'geheim'}],'note':'geheim','kind':'rating'})
        self.assertNotIn('geheim',str(kept));self.assertIn('kind',kept);self.assertNotIn('text',kept)

if __name__=='__main__':unittest.main()
