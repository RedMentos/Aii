import hashlib
import unittest

from scripts.run482_revision_scoped_quote_candidate import revision_scoped_choices


def row(doc_id, revision, body):
    return {'doc_id': doc_id, 'revision': revision, 'body': body,
            'sha256': hashlib.sha256(body.encode('utf-8')).hexdigest()}


def simple_ranker(bodies, goal, cap):
    # Test the boundary independently of Run481's lexical implementation.
    return [(i, 0, len(b)) for i, b in enumerate(bodies) if goal in b][:cap]


class RevisionScopedQuotes(unittest.TestCase):
    def test_historical_rule_never_reaches_ranker(self):
        old = row('policy', 1, 'Budget 10 euros.')
        new = row('policy', 2, 'Budget 90 euros.')
        seen = []
        def ranker(bodies, goal, cap):
            seen.extend(bodies)
            return simple_ranker(bodies, goal, cap)
        out = revision_scoped_choices([old, new], 'Budget',
                                      {'policy': new['sha256']}, ranker=ranker)
        self.assertEqual(seen, ['Budget 90 euros.'])
        self.assertEqual([c['source_index'] for c in out['choices']], [1])
        self.assertEqual(out['choices'][0]['text'], new['body'])
        self.assertFalse(out['canonical_gate_pass'])
        self.assertEqual(out['latent_authority'], 0)

    def test_multi_document_reindex_and_current_only(self):
        a0 = row('a', 0, 'Old alpha.')
        b0 = row('b', 0, 'Budget beta.')
        a1 = row('a', 1, 'Budget alpha.')
        out = revision_scoped_choices([a0, b0, a1], 'Budget',
                                      {'a': a1['sha256'], 'b': b0['sha256']},
                                      ranker=simple_ranker)
        self.assertEqual([c['source_index'] for c in out['choices']], [1, 2])
        self.assertEqual([c['revision'] for c in out['choices']], [0, 1])

    def test_stale_or_missing_pin_rejected(self):
        old, new = row('x', 1, 'Old.'), row('x', 2, 'New.')
        for docs, pins in [([new], {'x': old['sha256']}),
                           ([new], {'y': new['sha256']}),
                           ([new], {}),
                           ([new], {'x': '0'*64})]:
            with self.subTest(pins=pins), self.assertRaises(ValueError):
                revision_scoped_choices(docs, 'New', pins, ranker=simple_ranker)

    def test_forged_body_and_duplicate_revision_rejected(self):
        a = row('x', 1, 'Budget 40.')
        bad = dict(a, body='Budget 41.')
        for docs in ([bad], [a, a], [a, dict(a, revision=2)]):
            with self.subTest(docs=docs), self.assertRaises(ValueError):
                revision_scoped_choices(docs, 'Budget', {'x': a['sha256']},
                                        ranker=simple_ranker)

    def test_ranker_cannot_return_invalid_or_duplicate_pointers(self):
        a = row('x', 1, 'Budget.')
        invalid = [[(True, 0, 4)], [(0, -1, 2)], [(0, 0, 100)],
                   [(0, 0, 1), (0, 0, 1)], [(1, 0, 1)], [(0, 0, 0)]]
        for pointers in invalid:
            with self.subTest(pointers=pointers), self.assertRaises(ValueError):
                revision_scoped_choices([a], 'Budget', {'x': a['sha256']},
                                        ranker=lambda *args: pointers)

    def test_budget_and_type_fail_closed(self):
        a = row('x', 1, 'Budget.')
        bad = [(None, 'Budget', {'x': a['sha256']}, 1),
               ([a], True, {'x': a['sha256']}, 1),
               ([a], 'Budget', {'x': a['sha256']}, True),
               ([a], 'Budget', {'x': a['sha256']}, 25),
               ([a], 'Budget', {'x': a['sha256'].upper()}, 1),
               ([dict(a, revision=True)], 'Budget', {'x': a['sha256']}, 1)]
        for docs, goal, pins, cap in bad:
            with self.subTest(goal=goal, cap=cap), self.assertRaises(ValueError):
                revision_scoped_choices(docs, goal, pins, cap, ranker=simple_ranker)

    def test_shadow_empty_when_no_matching_current(self):
        a = row('x', 1, 'Budget 10.')
        out = revision_scoped_choices([a], 'deadline', {'x': a['sha256']},
                                      ranker=simple_ranker)
        self.assertEqual(out['choices'], [])
        self.assertEqual(out['step2_exit'], 'UTILITY_FAIL')
        self.assertEqual(out['b3_l1'], 'FAIL')
        self.assertEqual(out['jepa_weight'], 0)

    def test_integration_with_run481_lexical_ranker(self):
        old = row('policy', 1, 'Budget 10 euros. Deadline 4 days.')
        new = row('policy', 2, 'Budget 90 euros. Deadline 8 days.')
        out = revision_scoped_choices([old, new], 'budget deadline',
                                      {'policy': new['sha256']})
        self.assertEqual([c['text'] for c in out['choices']],
                         ['Budget 90 euros.', 'Deadline 8 days.'])
        self.assertTrue(all(c['source_index'] == 1 for c in out['choices']))


if __name__ == '__main__':
    unittest.main()
