"""Synthetic four-arm STEP2 evidence contracts; no native inference."""
import copy
import hashlib
import unittest

from scripts.step2_longnote_fourarm_analysis import ARMS, SEEDS, VARIANTS, analyze, validate

IDS = tuple(f'Project{i}' for i in range(10))


def sha(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def fixture():
    rows = []
    for arm in ARMS:
        for seed in SEEDS:
            scores = {}
            for i, fid in enumerate(IDS):
                for variant in VARIANTS:
                    v = {'b1_only': .7 if i == 0 else .3,
                         'b2_only': .7 if i == 1 else .4,
                         'both_none': .2, 'both_exact': {'TP': .95, 'TC': .55,
                                                        'SP': .60, 'SC': .45}[arm],
                         'both_control': .4, 'same_policy_dual': .35,
                         'prompt_only_dual': .4}[variant]
                    scores[f'{fid}:{variant}'] = v
            distinct = arm.startswith('T')
            rows.append({
                'arm': arm, 'seed': seed,
                'registration_sha256': '1' * 64,
                'fixture_sha256': '2' * 64,
                'runner_sha256': '3' * 64,
                'raw_sha256': sha(f'{arm}:{seed}'),
                'source_sha256': {f'file{i}.py': str(i) * 64 for i in range(4)},
                'model_sha256': {'B1_DETAIL': 'a' * 64,
                                 'B2_GIST': ('b' if distinct else 'a') * 64,
                                 'C3_LANGUAGE': 'c' * 64},
                'enable': {'seed': seed,
                           'b2_control': 'two_body' if distinct else 'shared_body_dual_state',
                           'b2_quote_select': 'pointer' if arm.endswith('P') else 'off',
                           'offer_quote_context_chars': 200,
                           'b1_recent_source_chars': 600,
                           'b2_offer_body_state': False},
                'queried_offers': {'offers': 20, 'with_question': 20},
                'step2_status': 'UTILITY_FAIL',
                'tool_status': 'TOOL_UTILITY_FAIL', 'evidence_kind': 'SOFTWARE_SYNTHETIC',
                'episode_utility_tool': scores,
                'error_profile_tool': {'b1_only': {'rule_fields_correct': .2,
                                                   'option_fields_correct': .9},
                                       'b2_only': {'rule_fields_correct': .9,
                                                   'option_fields_correct': .2}},
            })
    return rows


class FourArmAnalysis(unittest.TestCase):
    def test_complete_paired_synthetic_control_can_be_candidate_only(self):
        rows = fixture()
        baseline = copy.deepcopy(rows)
        report = analyze(rows, IDS)
        self.assertTrue(report['candidate_supported'])
        self.assertTrue(all(report['checks'].values()))
        self.assertEqual(report['comparisons']['tp_vs_shared_pointer']['episodes'], 10)
        self.assertGreater(report['comparisons']['tp_vs_shared_pointer']['ci95'][0], 0)
        self.assertFalse(report['canonical_gate_pass'])
        self.assertFalse(report['step2_gate_promoted'])
        self.assertFalse(report['body_jepa_available'])
        self.assertEqual(report['jepa_weight'], 0)
        self.assertEqual(rows, baseline)
        self.assertEqual(report, analyze(rows, IDS))

    def test_no_gain_preserves_negative_candidate(self):
        rows = fixture()
        for row in rows:
            if row['arm'] == 'TP':
                for fid in IDS:
                    row['episode_utility_tool'][f'{fid}:both_exact'] = .2
        result = analyze(rows, IDS)
        self.assertFalse(result['candidate_supported'])
        self.assertFalse(result['checks']['tp_beats_shared_pointer'])
        self.assertFalse(result['canonical_gate_pass'])

    def test_rejects_missing_duplicate_stale_and_wrong_provenance(self):
        cases = []
        rows = fixture(); cases.append(rows[:-1])
        rows = fixture(); rows[-1] = copy.deepcopy(rows[0]); cases.append(rows)
        rows = fixture(); rows[1]['raw_sha256'] = rows[0]['raw_sha256']; cases.append(rows)
        rows = fixture(); rows[1]['fixture_sha256'] = '9' * 64; cases.append(rows)
        rows = fixture(); rows[1]['registration_sha256'] = '9' * 64; cases.append(rows)
        rows = fixture(); rows[1]['source_sha256']['file0.py'] = '9' * 64; cases.append(rows)
        rows = fixture(); rows[1]['runner_sha256'] = '9' * 64; cases.append(rows)
        rows = fixture(); rows[1]['evidence_kind'] = 'REDMI_NATIVE'; cases.append(rows)
        rows = fixture(); rows[1]['model_sha256']['C3_LANGUAGE'] = '9' * 64; cases.append(rows)
        rows = fixture(); rows[1]['model_sha256']['B2_GIST'] = 'a' * 64; cases.append(rows)
        rows = fixture(); rows[3]['enable']['b2_quote_select'] = 'off'; cases.append(rows)
        rows = fixture(); rows[1]['queried_offers']['with_question'] = 19; cases.append(rows)
        rows = fixture(); rows[1]['step2_status'] = 'DIAGNOSTIC_INCOMPLETE'; cases.append(rows)
        rows = fixture(); rows[1]['tool_status'] = 'STRUCTURAL_FAIL'; cases.append(rows)
        rows = fixture(); rows[1]['tool_status'] = 'RUNNING'; cases.append(rows)
        rows = fixture(); rows[1]['tool_status'] = 'NOT_RUN'; cases.append(rows)
        rows = fixture(); rows[1]['tool_status'] = 'PREREGISTERED_NO_INFERENCE'; cases.append(rows)
        rows = fixture(); rows[1]['episode_utility_tool'].pop(f'{IDS[0]}:b1_only'); cases.append(rows)
        rows = fixture(); rows[1]['episode_utility_tool'][f'{IDS[0]}:b1_only'] = float('nan'); cases.append(rows)
        rows = fixture(); rows[1]['episode_utility_tool'][f'{IDS[0]}:b1_only'] = True; cases.append(rows)
        rows = fixture(); rows[1]['error_profile_tool']['b1_only']['rule_fields_correct'] = float('inf'); cases.append(rows)
        for i, row in enumerate(cases):
            with self.subTest(i=i), self.assertRaises(ValueError):
                analyze(row, IDS)

    def test_rejects_unregistered_fixture_and_control(self):
        rows = fixture()
        for ids in (IDS[:-1], IDS[:-1] + (IDS[0],), ('bad:fixture',) + IDS[1:]):
            with self.assertRaises(ValueError):
                validate(rows, ids)
        rows[0]['seed'] = True
        with self.assertRaises(ValueError):
            validate(rows, IDS)


if __name__ == '__main__':
    unittest.main()
