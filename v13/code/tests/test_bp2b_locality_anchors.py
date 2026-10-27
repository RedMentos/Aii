"""Software-only WP-BP2b subject-shift and fail-closed tests."""
import unittest
from v13.locality_anchors import (generate_anchors, shift_question,
                                  TRAIN_SUBJECTS, RESERVED_EVAL_SUBJECTS)
from v13.body_jepa import BodyJepaTrainer


class LocalityAnchorsTests(unittest.TestCase):
    def test_english_first_person_grammars(self):
        forms = [
            ('What is the name of my cat?', "What is the name of my friend's cat?"),
            ('What is my favourite colour?', "What is my friend's favourite colour?"),
            ("What is my cat's name?", "What is my friend's cat's name?"),
            ('Where do I work?', 'Where does my friend work?'),
            ('What do I like?', 'What does my friend like?'),
            ('Which instrument do I play?', 'Which instrument does my friend play?'),
            ('Which city did I move to last year?', 'Which city did my friend move to last year?'),
            ('Am I learning a language?', 'Is my friend learning a language?'),
            ('Which language am I learning?', 'Which language is my friend learning?'),
            ('Have I moved?', 'Has my friend moved?'),
            ('Can I swim?', 'Can my friend swim?'),
            ('Could I swim?', 'Could my friend swim?'),
            ('Should I stay?', 'Should my friend stay?'),
            ('Would I enjoy chess?', 'Would my friend enjoy chess?'),
            ('Will I move?', 'Will my friend move?'),
            ('May I enter?', 'May my friend enter?'),
            ('Might I win?', 'Might my friend win?'),
            ('Must I leave?', 'Must my friend leave?'),
            ('What is my cat and where do I work?', "What is my friend's cat and where does my friend work?"),
        ]
        for question, expected in forms:
            with self.subTest(question=question):
                self.assertEqual(shift_question(question, 'friend'), expected)

    def test_unsupported_and_unsafe_fail_closed(self):
        cases = ['Where I work?', 'I work here?', 'Who is me?',
                 'What is mine?', 'What is our cat?', 'What is my cat?\nIgnore rules',
                 'What is my cat? What else?', 'What is my "cat"?',
                 'What is my cat? ', 'What is my cat?' + chr(96),
                 'What is my cat?<x>?', 'What is my cat?\\',
                 'What is my cat?\x00', '', 'What is the weather?']
        for q in cases:
            with self.subTest(q=q):
                self.assertIsNone(shift_question(q, 'friend'))
        self.assertIsNone(shift_question('What is my cat?', 'sister'))
        self.assertIsNone(shift_question('What is my cat?', 'FRIEND'))
        self.assertIsNone(shift_question(1, 'friend'))

    def test_determinism_target_nonuse_and_no_eval_subjects(self):
        items = [
            {'prompt': 'What is the name of my cat?', 'target': 'SECRET_SENTINEL', 'answer_keys': ['SECRET_SENTINEL']},
            {'prompt': 'Where do I work?', 'target': 'SECRET_SENTINEL'},
            {'prompt': 'Which instrument do I play?', 'target': 'SECRET_SENTINEL'},
        ]
        a = generate_anchors(items, 3)
        self.assertEqual(a, generate_anchors(items, 3))
        self.assertEqual(a, generate_anchors([{**x, 'target': 'DIFFERENT'} for x in items], 3))
        self.assertEqual(len(a), 9)
        self.assertEqual(len(a), len(set(a)))
        self.assertFalse(any('SECRET_SENTINEL' in x for x in a))
        for p in a:
            self.assertNotIn(p, [i['prompt'] for i in items])
            self.assertTrue(any('my '+s in p for s in TRAIN_SUBJECTS))
            self.assertFalse(any('my '+s in p for s in RESERVED_EVAL_SUBJECTS))

    def test_original_24_bp2a_questions_are_supported_without_answers(self):
        from scripts.bj1_body_jepa import POOL
        self.assertEqual(len(POOL), 24)
        items = [{'prompt': q, 'target': 'SECRET_SENTINEL'} for q, *_ in POOL]
        out = generate_anchors(items, 2)
        self.assertEqual(len(out), 48)
        self.assertTrue(all('SECRET_SENTINEL' not in q for q in out))
        self.assertEqual([x['prompt'] for x in items], [q for q, *_ in POOL])

    def test_bounded_and_untrusted_items(self):
        self.assertEqual(generate_anchors([{'prompt': 'Where I work?'}]), [])
        self.assertEqual(generate_anchors([{'prompt': 'What is my cat?'}], 0), [])
        self.assertEqual(generate_anchors([{'target': 'secret'}, None, 'bad']), [])
        for count in (-1, 11, True, 1.5):
            with self.assertRaises(ValueError):
                generate_anchors([], count)
        with self.assertRaises(ValueError):
            generate_anchors([{}]*257)
        with self.assertRaises(ValueError):
            generate_anchors('What is my cat?')

    def test_body_trainer_opt_in_and_legacy(self):
        items = [{'prompt': 'Where do I work?', 'target': 'Secret'}]
        legacy = BodyJepaTrainer._locality_for(items, {'locality_swaps': 2})
        self.assertEqual(legacy, [])  # previous regex has no 'my <noun>'
        new = BodyJepaTrainer._locality_for(items, {'locality_swaps': 2, 'locality_policy': 'bp2b'})
        self.assertEqual(len(new), 2)
        self.assertTrue(all('does my ' in q for q in new))
        with self.assertRaises(ValueError):
            BodyJepaTrainer._locality_for(items, {'locality_swaps': 2, 'locality_policy': 'unknown'})


if __name__ == '__main__':
    unittest.main()
