import copy
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import age_source_lineage_guard as G


def registry(roots=('r0', 'r1', 'r2', 'r3')):
    return {'schema': G.REGISTRY_SCHEMA,
            'sources': [{'source_id': f's{i}', 'root_id': root, 'quality': 1.}
                        for i, root in enumerate(roots)]}


def votes(flip=False):
    return [{'case_id': f'case{i}', 'source_id': f's{j}',
             'label': (i + int(flip)) % 2, 'source_quality': 1.}
            for i in range(5) for j in range(4)]


class RootLineage(unittest.TestCase):
    def test_known_correlated_aliases_cannot_fake_independent_majority(self):
        r = G.assess(votes(), votes(True), registry(('root',)*4))
        self.assertEqual(r['status'], 'INSUFFICIENT_EVIDENCE')
        self.assertEqual(r['root_alias_rows_collapsed'], 30)
        self.assertEqual(r['registered_roots'], 1)
        self.assertFalse(r['canonical_gate_pass'])

    def test_distinct_claimed_roots_still_unverified(self):
        r = G.assess(votes(), votes(True), registry())
        self.assertEqual(r['status'], 'UNVERIFIED_SHIFT_SIGNAL')
        self.assertEqual(r['diagnostic']['status'], 'SHIFT_CANDIDATE')
        self.assertFalse(r['registry_authenticated'])
        self.assertFalse(r['source_independence_verified'])
        self.assertEqual(r['authority'], 'SHADOW_NO_AGE_ACTION')

    def test_two_roots_each_aliased_do_not_inflate_votes(self):
        r = G.assess(votes(), votes(True), registry(('a','a','b','b')))
        self.assertEqual(r['status'], 'UNVERIFIED_SHIFT_SIGNAL')
        self.assertEqual(r['registered_roots'], 2)
        self.assertEqual(r['root_alias_rows_collapsed'], 20)

    def test_conflicting_aliases_reject(self):
        cur = votes(True)
        cur[1]['label'] = 1-cur[1]['label']
        with self.assertRaisesRegex(ValueError, 'conflicting aliases'):
            G.assess(votes(), cur, registry(('a','a','b','b')))

    def test_registry_duplicate_source_reject(self):
        r = registry(); r['sources'].append(copy.deepcopy(r['sources'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate source'):
            G.assess(votes(), votes(), r)

    def test_registry_alias_root_change_does_not_look_authenticated(self):
        r = registry()
        first = G.assess(votes(), votes(True), r)
        r['sources'][0]['root_id'] = 'r1'
        second = G.assess(votes(), votes(True), r)
        self.assertNotEqual(first['registry_sha256'], second['registry_sha256'])
        self.assertFalse(second['registry_authenticated'])

    def test_unknown_source_reject_even_low_quality(self):
        v = votes(); v[0]['source_id'] = 'spoof'; v[0]['source_quality'] = .0
        with self.assertRaisesRegex(ValueError, 'unregistered'):
            G.assess(v, votes(), registry())

    def test_quality_cannot_be_inflated_by_observation(self):
        r = registry()
        for source in r['sources']: source['quality'] = .4
        self.assertEqual(G.assess(votes(), votes(True), r)['status'], 'INSUFFICIENT_EVIDENCE')

    def test_quality_cannot_be_inflated_by_registry(self):
        v = votes(); w = votes(True)
        for row in v+w: row['source_quality'] = .3
        self.assertEqual(G.assess(v, w, registry())['status'], 'INSUFFICIENT_EVIDENCE')

    def test_malformed_observations_fail_closed(self):
        for bad in (None, [], [{'case_id': 'c', 'source_id': 's0', 'label': True, 'source_quality': 1.}],
                    [{'case_id': 'c', 'source_id': 's0', 'label': 0, 'source_quality': math.nan}],
                    [{'case_id': 'c', 'source_id': 's0', 'label': 0, 'source_quality': 1., 'extra': 1}]):
            with self.subTest(bad=bad):
                if bad == []: continue  # empty window is legitimate insufficient evidence
                with self.assertRaises(ValueError): G.assess(bad, votes(), registry())

    def test_registry_rejects_nonfinite_and_extra(self):
        for value in (math.inf, math.nan, -1, 1.1, True):
            r = registry(); r['sources'][0]['quality'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                G.assess(votes(), votes(), r)
        r = registry(); r['sources'][0]['trusted'] = True
        with self.assertRaisesRegex(ValueError, 'closed registry'):
            G.assess(votes(), votes(), r)

    def test_deterministic_reordered_votes(self):
        r = registry()
        self.assertEqual(G.assess(votes(), votes(True), r),
                         G.assess(list(reversed(votes())), list(reversed(votes(True))), r))

    def test_conflicting_duplicate_exact_source_reject(self):
        v = votes(); extra = dict(v[0]); extra['label'] = 1-extra['label']; v.append(extra)
        with self.assertRaisesRegex(ValueError, 'conflicting aliases'):
            G.assess(v, votes(), registry())

    def test_empty_window_is_not_a_shift(self):
        self.assertEqual(G.assess([], votes(), registry())['status'], 'INSUFFICIENT_EVIDENCE')

if __name__ == '__main__': unittest.main()
