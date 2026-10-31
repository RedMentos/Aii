"""Fixed G-FOCAL-CAPACITY-003 pressure controls; candidate remains default OFF."""
from copy import deepcopy
import itertools
import json
from pathlib import Path
import tempfile
import unittest

from scripts import focal_capacity_diversity_candidate_20261031 as candidate
from v13 import focal
from v13.config import initialize
from v13.store import Store


class FocalCapacityPressure(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        home = Path(self.temp.name)
        initialize(home)
        self.store = Store(home)
        self.addCleanup(self.store.close)
        self.items = candidate.pressure_fixture(self.store)

    def test_actual_baseline_duplicate_trap_and_candidate_diversity(self):
        baseline, _ = focal.admit(deepcopy(self.items), 2, .45)
        selected, _ = candidate.admit_diverse(deepcopy(self.items), 2, .45)
        a = candidate.evidence(self.store, baseline)
        b = candidate.evidence(self.store, selected)
        self.assertEqual(a['ids'], ['A', 'B'])
        self.assertEqual(b['ids'], ['A', 'C'])
        self.assertEqual(a['distinct_source_ids'], 1)
        self.assertEqual(b['distinct_source_ids'], 2)
        self.assertGreater(b['marginal_priority_sum'], a['marginal_priority_sum'])
        self.assertTrue(a['refs_readable'] and b['refs_readable'])

    def test_all_distinct_control_does_not_reduce_coverage(self):
        rows = deepcopy(self.items)
        for i, row in enumerate(rows):
            text = 'Unique nonoverlapping alpha{} phrase{} proof{}'.format(
                'X' * (i + 1), 'Y' * (i + 2), 'Z' * (i + 3))
            row['text'] = text
            row['source_refs'] = [self.store.source(text)]
        original, _ = focal.admit(deepcopy(rows), 2, .45)
        selected, _ = candidate.admit_diverse(deepcopy(rows), 2, .45)
        self.assertEqual(len(original), len(selected))
        self.assertGreaterEqual(candidate.evidence(self.store, selected)['distinct_source_ids'],
                                candidate.evidence(self.store, original)['distinct_source_ids'])

    def test_high_salience_interrupt_respected_at_capacity_one(self):
        rows = deepcopy([self.items[0], self.items[2]])
        rows[1]['salience'] = .95
        baseline, _ = focal.admit(deepcopy(rows), 1, .45)
        selected, _ = candidate.admit_diverse(deepcopy(rows), 1, .45)
        self.assertEqual([x['item_id'] for x in baseline], ['C'])
        self.assertEqual([x['item_id'] for x in selected], ['C'])
        self.assertEqual(selected[0]['state_type'], 'ACTIVE')

    def test_dropped_and_below_threshold_do_not_gain_authority(self):
        rows = deepcopy(self.items)
        rows[1]['state_type'] = 'DROPPED'
        selected, rest = candidate.admit_diverse(rows, 2, .45)
        self.assertNotIn('B', [x['item_id'] for x in selected])
        self.assertEqual(next(x for x in rest if x['item_id'] == 'B')['state_type'],
                         'DROPPED')
        none, rejected = candidate.admit_diverse(deepcopy(self.items), 2, 1.)
        self.assertEqual(none, [])
        self.assertEqual(len(rejected), 3)
        self.assertTrue(all(x['state_type'] != 'ACTIVE' for x in rejected))

    def test_permutation_determinism_and_exact_refs_unchanged(self):
        ids = set()
        for order in itertools.permutations(self.items):
            rows = deepcopy(list(order))
            before = {x['item_id']: deepcopy(x['source_refs']) for x in rows}
            selected, rest = candidate.admit_diverse(rows, 2, .45)
            ids.add(tuple(x['item_id'] for x in selected))
            self.assertEqual({x['item_id']: x['source_refs'] for x in rows}, before)
            self.assertEqual(len(selected) + len(rest), len(rows))
            for x in rows:
                self.assertIn(x['fact_hypothesis_status'], ('HYPOTHESIS', 'PRIOR_HYPOTHESIS'))
                for ref in x['source_refs']:
                    self.store.read_source(ref)
        self.assertEqual(ids, {('A', 'C')})

    def test_invalid_capacity_bounds_and_duplicate_ids_fail_closed(self):
        for capacity in (-1, True, 1.2):
            with self.assertRaises(ValueError):
                candidate.admit_diverse(deepcopy(self.items), capacity)
        for threshold in (float('nan'), -1, 1.1, True):
            with self.assertRaises(ValueError):
                candidate.admit_diverse(deepcopy(self.items), 2, threshold)
        rows = deepcopy(self.items)
        rows[1]['item_id'] = rows[0]['item_id']
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_ITEM_ID'):
            candidate.admit_diverse(rows)

    def test_report_is_explicitly_software_only_and_nonpromoting(self):
        report = candidate.evaluate()
        self.assertEqual(report['schema'], candidate.SCHEMA)
        self.assertEqual(report['baseline']['ids'], ['A', 'B'])
        self.assertEqual(report['candidate']['ids'], ['A', 'C'])
        self.assertFalse(report['native_model_used'])
        self.assertFalse(report['redmi_measured'])
        self.assertFalse(report['semantic_utility_proven'])
        self.assertFalse(report['gate_promoted'])
        self.assertNotIn('authority', json.dumps(report))


if __name__ == '__main__':
    unittest.main()
