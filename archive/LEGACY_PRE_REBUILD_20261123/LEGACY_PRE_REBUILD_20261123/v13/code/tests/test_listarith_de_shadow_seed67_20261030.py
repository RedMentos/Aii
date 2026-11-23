"""Seed67 dev-only German list_arith SHADOW tests; holdout is evaluated separately."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import types
import unittest

CODE = Path(__file__).resolve().parents[1]
SPEC = CODE / 'specs' / 'listarith_de_shadow_seed67_fixtures.json'
sys.path.insert(0, str(CODE))

try:
    from v13.agi import listarith as english
    from v13.agi import listarith_de_shadow as german
    REAL_IMPORT = True
except ImportError:
    REAL_IMPORT = False
    def question_part(text):
        parts = [p for p in re.split(r'(?<=[.!?\"])\s+', str(text).strip()) if p]
        tail = []
        for p in reversed(parts):
            if re.search(r'\d', p):
                break
            tail.insert(0, p)
        return ' '.join(tail) if tail else (parts[-1] if parts else str(text))
    for name in ('v13', 'v13.agi'):
        mod = types.ModuleType(name)
        mod.__path__ = []
        sys.modules[name] = mod
    english = types.ModuleType('v13.agi.listarith')
    english.question_part = question_part
    english.MAX_TEXT = 2000
    sys.modules['v13.agi.listarith'] = english
    spec = importlib.util.spec_from_file_location('v13.agi.listarith_de_shadow', CODE/'v13'/'agi'/'listarith_de_shadow.py')
    german = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(german)


def rows():
    return json.loads(SPEC.read_text())


def canonical_sha(data):
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


class GermanShadowDev(unittest.TestCase):
    def test_frozen_cohort_and_dev_identity(self):
        data = rows()
        self.assertEqual(len(data), 48)
        self.assertEqual(canonical_sha(data), '468b231fd196f28e773fba1d541f4ed7c7436d180d78b835e0ad3eb3f85a3d05')
        self.assertEqual(len([x for x in data if x['split']=='dev']), 24)
        self.assertEqual(len([x for x in data if x['split']=='holdout']), 24)
        self.assertEqual(len({x['id'] for x in data}), 48)

    def test_all_24_dev_labels_and_no_action_authority(self):
        dev = [x for x in rows() if x['split']=='dev']
        failed = []
        for x in dev:
            got = german.propose(x['text'])
            self.assertEqual(got['authority'], 'SHADOW_ONLY')
            if got['proposal'] != x['expected']:
                failed.append((x['id'], got['proposal'], x['expected']))
        self.assertEqual(failed, [])

    def test_fail_closed_conflict_ambiguity_and_length(self):
        cases = [None, 3, '', 'x'*2001,
                 'Werte: A 12, B 30. Wie hoch sind Summe und Differenz zwischen größtem und kleinstem Wert?',
                 'Werte: A 12, B 30. Wie viel mehr hat A als B?',
                 'Werte: A 12, B 30. Wie hoch ist die Gesamtzahl der Positionen?',
                 'Werte: A 12, B 30. Wie groß ist der Durchschnitt?']
        for text in cases:
            got = german.propose(text)
            self.assertIsNone(got['proposal'], text)
            self.assertEqual(got['authority'], 'SHADOW_ONLY')

    def test_question_only_ignores_source_data_summary(self):
        text = 'Werte: A 12, B 30. Gesamtsumme: 42. Wie viele Einträge gibt es insgesamt?'
        self.assertIsNone(german.propose(text)['proposal'])

    def test_no_production_wiring_or_tool_execution(self):
        self.assertFalse(hasattr(german, 'tool'))
        self.assertFalse(hasattr(german, 'run'))
        self.assertEqual(german.AUTHORITY, 'SHADOW_ONLY')
        self.assertTrue(german.REVISION.startswith('listarith-de-shadow-'))

    @unittest.skipUnless(REAL_IMPORT, 'Original English registrar unavailable in isolated source fixture')
    def test_original_english_operation_regressions(self):
        cases = [
            ('Items: A 12, B 30. What is the total?', 'total'),
            ('Items: A 12, B 30. What is the sum?', 'total'),
            ('Items: A 12, B 30. How much more is the largest than the smallest?', 'difference_max_min'),
            ('Items: A 12, B 30. How much less is the smallest than the largest?', 'difference_max_min'),
            ('Items: A 12, B 30. How many total number of entries?', None),
            ('Items: A 12, B 30. What is the average?', None),
            ('Items: A 12, B 30. Add them up.', 'total'),
            ('Items: A 12, B 30. What is the gap between them?', 'difference_max_min'),
        ]
        for text, want in cases:
            self.assertEqual(english.operation(text), want, text)


if __name__ == '__main__':
    unittest.main()