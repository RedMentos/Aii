import hashlib
import unittest
from scripts.run483_b3_l1_seed_pins import REQUIRED, digest, evaluate_pinned


def fixture():
    rows = []
    for ch in REQUIRED:
        for seed in ('s1', 's2', 's3'):
            rows.append({'channel': ch, 'seed': seed,
                         'accuracy': 1.0 if ch == 'LATENT' else 0.0,
                         'bytes': 8, 'evidence_sha256': hashlib.sha256((ch + seed).encode()).hexdigest()})
    pins = {r['channel'] + '/' + r['seed']: digest(r) for r in rows}
    meta = {'role_drop': 0.0, 'ood_rate': 0.0, 'reload_identical': True}
    return rows, pins, meta, digest(meta)


def fake_evaluator(task):
    assert all(len(v) == 3 for v in task['acc'].values())
    return {'canonical_gate_pass': False, 'latent_authority': 0,
            'b3_l1': 'FAIL', 'diagnostic_l1_verdict': 'PASS'}


class PinnedSeedRows(unittest.TestCase):
    def test_complete_pinned_matrix_no_authority(self):
        rows, pins, meta, mp = fixture()
        out = evaluate_pinned(rows, pins, meta, mp, evaluator=fake_evaluator)
        self.assertEqual(out['row_count'], 21)
        self.assertEqual(out['seed_ids'], ['s1', 's2', 's3'])
        self.assertFalse(out['canonical_gate_pass'])
        self.assertEqual(out['diagnostic_l1_verdict'], 'PASS')
        self.assertEqual(out['b3_l1'], 'FAIL')

    def test_row_content_swap_with_same_cohort_rejected(self):
        rows, pins, meta, mp = fixture()
        rows[0]['accuracy'] = 0.1
        with self.assertRaisesRegex(ValueError, 'B3_PINNED_ROW_MISMATCH'):
            evaluate_pinned(rows, pins, meta, mp, evaluator=fake_evaluator)

    def test_missing_or_extra_seed_refused(self):
        rows, pins, meta, mp = fixture()
        rows.pop()
        with self.assertRaises(ValueError):
            evaluate_pinned(rows, pins, meta, mp, evaluator=fake_evaluator)
        rows, pins, meta, mp = fixture()
        rows[0]['seed'] = 's4'
        with self.assertRaises(ValueError):
            evaluate_pinned(rows, pins, meta, mp, evaluator=fake_evaluator)

    def test_duplicate_rows_rejected_but_shared_artifact_allowed(self):
        rows, pins, meta, mp = fixture()
        rows[1]['evidence_sha256'] = rows[0]['evidence_sha256']
        pins['NO_MESSAGE/s2'] = digest(rows[1])
        self.assertEqual(evaluate_pinned(rows, pins, meta, mp, evaluator=fake_evaluator)['row_count'], 21)
        rows, pins, meta, mp = fixture()
        rows[1] = rows[0].copy()
        with self.assertRaisesRegex(ValueError, 'B3_PINNED_DUPLICATE_ROW'):
            evaluate_pinned(rows, pins, meta, mp, evaluator=fake_evaluator)

    def test_metadata_mutation_and_nonfinite_rejected(self):
        rows, pins, meta, mp = fixture()
        meta['role_drop'] = 0.2
        with self.assertRaisesRegex(ValueError, 'B3_PINNED_METADATA_MISMATCH'):
            evaluate_pinned(rows, pins, meta, mp, evaluator=fake_evaluator)
        rows, pins, meta, mp = fixture()
        rows[0]['accuracy'] = float('nan')
        with self.assertRaisesRegex(ValueError, 'B3_PINNED_MEASUREMENT_INVALID'):
            evaluate_pinned(rows, pins, meta, mp, evaluator=fake_evaluator)

    def test_seed_specific_byte_cost_must_not_collapse(self):
        rows, pins, meta, mp = fixture()
        rows[0]['bytes'] = 16
        pins['NO_MESSAGE/s1'] = digest(rows[0])
        with self.assertRaisesRegex(ValueError, 'B3_PINNED_BYTES_VARY_BY_SEED'):
            evaluate_pinned(rows, pins, meta, mp, evaluator=fake_evaluator)

    def test_forged_evaluator_cannot_promote(self):
        rows, pins, meta, mp = fixture()
        with self.assertRaisesRegex(ValueError, 'B3_PINNED_EVALUATOR_PROMOTED'):
            evaluate_pinned(rows, pins, meta, mp,
                            evaluator=lambda task: {'canonical_gate_pass': True})

    def test_integration_with_real_run478(self):
        rows, pins, meta, mp = fixture()
        out = evaluate_pinned(rows, pins, meta, mp)
        self.assertEqual(out['diagnostic_l1_verdict'], 'PASS')
        self.assertEqual(out['step2_exit'], 'UTILITY_FAIL')
        self.assertEqual(out['b3_l1'], 'FAIL')


if __name__ == '__main__':
    unittest.main()
