"""Dream2 comparison reports retain incomplete cohorts and reject corrupt rows."""
import copy
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1]/'scripts/analyze_dream_ablation.py'
spec = importlib.util.spec_from_file_location('dream_analysis', SCRIPT)
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


def fixture():
    evaluation = {'A': {'recall': 1., 'paraphrase': .5},
                  'B': {'recall': 1., 'paraphrase': .5},
                  'probe_retention': .8, 'near_miss_leak': .2, 'kl_to_base': .01}
    rows = []
    for seed in analysis.SEEDS:
        for arm in analysis.ARMS:
            after = copy.deepcopy(evaluation)
            if arm == 'none': after['A']['recall'] = .75
            rows.append({'seed': seed, 'arm': arm, 'phase_a': {'steps': 12, 'items': 4}, 'phase_b': {'steps': 40},
                         'after_a': copy.deepcopy(evaluation), 'after_b': after,
                         'raw_generations': [{'prompt': 'synthetic software fixture', 'answer': 'fixture'}]})
    return {'schema': 'v13-dream-ablation-v1', 'proof_version': 2, 'status': 'COMPLETE',
            'phone_measured': False, 'canonical_gate_pass': False,
            'run_binding': {'config': {'seeds': list(analysis.SEEDS), 'b_steps': 40},
                            'arms': list(analysis.ARMS)},
            'runs': rows, 'row_sha256': [analysis.sha(analysis.encoded(row)) for row in rows]}


class DreamAnalysis(unittest.TestCase):
    def test_complete_deltas_preserve_control_directions_without_acceptance(self):
        result = analysis.analyze(fixture(), 'fixture source, no native claim')
        self.assertEqual(result['status'], 'COMPLETE_SCOPED_COMPARISONS')
        self.assertFalse(result['canonical_gate_pass'])
        seed = result['per_seed'][0]
        self.assertTrue(seed['forgetting_observed_without_rehearsal'])
        comparisons = seed['dream_control_deltas']
        self.assertEqual(comparisons[0]['candidate_minus_control']['A_recall'], .25)
        self.assertEqual(comparisons[1]['candidate_minus_control']['A_recall'], 0.)
        self.assertEqual(result['complete_cohort_arm_means']['none']['A_recall'], .75)

    def test_partial_never_becomes_complete_or_fills_missing_controls(self):
        doc = fixture(); doc['status'] = 'RUNNING'; doc['runs'] = doc['runs'][:2]; doc['row_sha256'] = doc['row_sha256'][:2]
        result = analysis.analyze(doc, 'fixture')
        self.assertEqual(result['status'], 'RUNNING_PARTIAL')
        self.assertEqual(len(result['missing_arms']), 13)
        self.assertEqual(result['per_seed'][0]['dream_control_deltas'], [])
        self.assertIsNone(result['complete_cohort_arm_means'])

    def test_tamper_duplicate_and_incomplete_complete_marker_rejected(self):
        doc = fixture(); doc['runs'][0]['after_b']['A']['recall'] = 0
        with self.assertRaisesRegex(ValueError, 'bytes changed'): analysis.analyze(doc, 'fixture')
        doc = fixture(); doc['runs'].append(doc['runs'][0]); doc['row_sha256'].append(doc['row_sha256'][0])
        with self.assertRaisesRegex(ValueError, 'duplicate'): analysis.analyze(doc, 'fixture')
        doc = fixture(); doc['runs'].pop(); doc['row_sha256'].pop()
        with self.assertRaisesRegex(ValueError, 'full cohort'): analysis.analyze(doc, 'fixture')

    def test_missing_seed_fixed_step_and_cloud_claim_rejected(self):
        for mutate in (lambda d: d['run_binding']['config'].update(seeds=[13, 21]),
                       lambda d: d['run_binding']['config'].update(b_steps=10),
                       lambda d: d.update(phone_measured=True)):
            doc = fixture(); mutate(doc)
            with self.assertRaises(ValueError): analysis.analyze(doc, 'fixture')

    def test_empty_raw_trace_and_absent_phase_a_rejected_even_with_updated_hash(self):
        for mutate in (lambda row: row.update(raw_generations=[]),
                       lambda row: row.pop('phase_a')):
            doc = fixture(); mutate(doc['runs'][0])
            doc['row_sha256'][0] = analysis.sha(analysis.encoded(doc['runs'][0]))
            with self.assertRaisesRegex(ValueError, 'Incomplete'): analysis.analyze(doc, 'fixture')


if __name__ == '__main__': unittest.main()
