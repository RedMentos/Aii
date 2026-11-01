"""WP-BP2b: near-miss anchor generator."""
import unittest
from v13 import locality_gen as lg


class LocalityGenTests(unittest.TestCase):
    def test_possessive_noun(self):
        self.assertEqual(lg.variants('What is the name of my cat?', ('friend', 'mother')),
                         ["What is the name of my friend's cat?", "What is the name of my mother's cat?"])

    def test_first_person_verbs(self):
        self.assertEqual(lg.variants('Where do I work?', ('boss',), 1), ['Where does my boss work?'])
        self.assertEqual(lg.variants('Which city did I move to last year?', ('cousin',), 1), ['Which city did my cousin move to last year?'])
        self.assertEqual(lg.variants('Which language am I learning?', ('uncle',), 1), ['Which language is my uncle learning?'])

    def test_no_pattern_means_no_anchor(self):
        self.assertEqual(lg.variants('What is the capital of France?'), [])
        out, rep = lg.anchors_for(['What is the capital of France?', 'Where do I work?'])
        self.assertEqual(rep['no_pattern'], ['What is the capital of France?'])
        self.assertEqual(rep['anchors'], 2)

    def test_no_duplicates_and_k_bound(self):
        v = lg.variants('When is my birthday?', k=3)
        self.assertEqual(len(v), 3)
        self.assertEqual(len(set(v)), 3)
        self.assertEqual(lg.variants('When is my birthday?', ('a',), 5), ["When is my a's birthday?"])

    def test_subjects_rotate_across_facts(self):
        out, _ = lg.anchors_for(['When is my birthday?', 'What is my blood type?', 'What is my street?'])
        owners = {a.split("my ")[1].split("'s")[0] for a in out}
        self.assertGreaterEqual(len(owners), 5)

    def test_train_subjects_do_not_overlap_bench_eval_subjects(self):
        for bad in ('dog', 'sister', 'wife', 'nephew', 'girlfriend', 'stepbrother', 'granddaughter', 'aunt'):
            self.assertNotIn(bad, lg.TRAIN_SUBJECTS)


if __name__ == '__main__':
    unittest.main()
