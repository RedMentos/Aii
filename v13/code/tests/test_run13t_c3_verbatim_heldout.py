"""Run13T disjoint source/prompt/verdict and synthetic verifier fault tests."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from scripts import run13t_c3_verbatim_heldout as t
from scripts import run13t_c3_verbatim_heldout_verify as v
from scripts import run13j_c3_jef_native as j
from scripts import run13j_c3_jef_native_verify as jverify
from scripts import run13k_c3_copy_native as k
from v13.agi.c3_source_fidelity_shadow_run13m import audit_source_facts

FIXTURE = Path(__file__).resolve().parents[1] / 'docs/fixtures/run13t_c3_verbatim_seed283_20261030.json'


class Run13TSoftware(unittest.TestCase):
    def test_frozen_disjoint_eight_case_fixture(self):
        cases = t.load_fixture(FIXTURE)
        self.assertEqual(len(cases), 8)
        self.assertEqual(j.fixture_hash(cases), t.FIXTURE_SHA256)
        self.assertEqual(len({x['project'] for x in cases}), 8)
        self.assertTrue(all(x['project'].endswith('283') for x in cases))
        self.assertEqual(t.SEED, 283)

    def test_only_system_changes_and_arms_counterbalance(self):
        answer = jverify.expected_answer(t.load_fixture(FIXTURE)[0])
        linked = v.source_link(answer)
        prompt = k.prompt_for(linked, 'COPY_DIRECT')
        self.assertEqual(prompt, k.COPY_PREFIX + answer + k.COPY_SUFFIX)
        self.assertEqual(t.system_for('COPY_BASELINE'), __import__(
            'scripts.run13l_c3_system_native', fromlist=['SYSTEM_COPY']).SYSTEM_COPY)
        self.assertNotEqual(t.system_for('COPY_BASELINE'), t.system_for('COPY_STRICT'))
        self.assertEqual(t.arm_order(0), t.ARMS)
        self.assertEqual(t.arm_order(1), tuple(reversed(t.ARMS)))
        with self.assertRaises(ValueError):
            t.system_for('UNKNOWN')

    def test_preregistered_diagnostic_never_promotes(self):
        base = {'n': 8, 'exact_copy': 1, 'strict_full': 3,
                'source_facts_verified': 3, 'wrong_claims': 0}
        good = {'n': 8, 'exact_copy': 3, 'strict_full': 3,
                'source_facts_verified': 3, 'wrong_claims': 0}
        self.assertEqual(t.verdict({'COPY_BASELINE': base, 'COPY_STRICT': good}),
                         'BOUNDED_SYNTHETIC_FIDELITY_SIGNAL_NOT_UTILITY_GATE')
        self.assertEqual(t.verdict({'COPY_BASELINE': base,
                                    'COPY_STRICT': dict(good, source_facts_verified=2)}),
                         'NO_ATTRIBUTABLE_FIDELITY_GAIN')
        self.assertEqual(t.verdict({'COPY_BASELINE': base,
                                    'COPY_STRICT': dict(good, wrong_claims=1)}),
                         'NO_ATTRIBUTABLE_FIDELITY_GAIN')
        self.assertEqual(t.verdict({'COPY_BASELINE': base,
                                    'COPY_STRICT': dict(good, strict_full=2)}),
                         'FIDELITY_HURT')
        with self.assertRaises(ValueError):
            t.verdict({'COPY_BASELINE': base,
                       'COPY_STRICT': dict(good, n=7)})

    def make_synthetic(self, directory):
        pilot = Path(directory)
        (pilot / 'raw').mkdir()
        cases = t.load_fixture(FIXTURE)
        rows = []
        for i, case in enumerate(cases):
            answer = jverify.expected_answer(case)
            prompt = k.COPY_PREFIX + answer + k.COPY_SUFFIX
            for ai, arm in enumerate(t.ARMS):
                pid = 10000 + 2 * i + ai
                output = answer
                score = j.score(case, output, True)
                fidelity = audit_source_facts(v.source_link(answer), output)
                row = {
                    'schema': t.SCHEMA, 'seed': t.SEED, 'index': i,
                    'project': case['project'], 'arm': arm,
                    'source_event_id': f'source{i}', 'query_event_id': f'query{i}',
                    'context_plan_packet_id': f'packet{i}',
                    'source_sha256': t.sha(j.frozen.prompt(case)),
                    'answer_sha256': t.sha(answer),
                    'prompt_sha256': t.sha(prompt),
                    'system_sha256': t.sha(t.system_for(arm)),
                    'model_sha256': t.MODEL_SHA, 'model_revision': t.MODEL_REVISION,
                    'learning_mode': 'RECORD_ONLY', 'jepa_weight': 0,
                    'step2_status': 'UTILITY_FAIL', 'b3_status': 'NO_PROMOTION',
                    'body_jepa_status': 'UNAVAILABLE', 'redmi_measured': False,
                    'whole_system_complete': False, 'native_role': 'C3_LANGUAGE',
                    'native_calls': 1, 'native_status': 'FINAL', 'native_pid': pid,
                    'native_reaped': True, 'final_output': output,
                    'native_release': {'process_reaped': True},
                    'native_metrics': {'status': 'FINAL', 'role': 'C3_LANGUAGE',
                                       'actual_model': 'LFM2.5-350M-QAD-Q4_0.gguf'},
                    'score': score, 'exact_copy': True,
                    'source_facts_verified': True, 'fidelity_reason': fidelity['reason'],
                    'wrong_claims': 0,
                }
                path = pilot / 'raw' / f'{i:02d}_{arm}.json'
                path.write_text(json.dumps(row))
                rows.append(row)
        totals = {arm: {
            'n': 8, 'native_final': 8, 'exact_copy': 8,
            'source_facts_verified': 8, 'wrong_claims': 0, 'numeric_correct': 16,
            'faster_correct': 8, 'strict_full': 8, 'literal_abstain_dot': 0,
        } for arm in t.ARMS}
        report = {'schema': t.SCHEMA, 'seed': t.SEED,
                  'fixture_sha256': t.FIXTURE_SHA256, 'rows': 16,
                  'totals': totals, 'status': t.verdict(totals),
                  'all_native_final': True, 'all_native_reaped': True,
                  'learning_mode': 'RECORD_ONLY', 'step2_status': 'UTILITY_FAIL',
                  'b3_status': 'NO_PROMOTION', 'body_jepa_status': 'UNAVAILABLE',
                  'jepa_weight': 0, 'redmi_measured': False,
                  'utility_gate_promoted': False, 'whole_system_complete': False,
                  'production_activation': False, 'semantic_quality_proven': False}
        (pilot / 'report.json').write_text(json.dumps(report))
        return pilot

    def test_explicit_wrong_claims_option_value_and_faster(self):
        case = t.load_fixture(FIXTURE)[0]
        good = jverify.expected_answer(case)
        self.assertEqual(t.explicit_wrong_claims(case, good), 0)
        self.assertEqual(t.explicit_wrong_claims(case, good.replace(
            str(case['budget'] - case['a_cost']), '9999')), 1)
        expected_faster = case['a'] if case['a_days'] < case['b_days'] else case['b']
        wrong_faster = case['b'] if expected_faster == case['a'] else case['a']
        self.assertEqual(t.explicit_wrong_claims(case, good.replace(
            expected_faster + ' finishes sooner', wrong_faster + ' finishes sooner')), 1)
        with self.assertRaises(ValueError):
            t.explicit_wrong_claims(case, None)

    def test_synthetic_verifier_and_corrupt_source_counterexample(self):
        with tempfile.TemporaryDirectory() as td:
            pilot = self.make_synthetic(td)
            result = v.verify(pilot, FIXTURE)
            self.assertEqual(result['native_rows'], 16)
            self.assertEqual(result['distinct_native_pids'], 16)
            path = pilot / 'raw/00_COPY_STRICT.json'
            row = json.loads(path.read_text())
            row['source_sha256'] = '0' * 64
            path.write_text(json.dumps(row))
            with self.assertRaisesRegex(ValueError, 'RUN13T_SOURCE_OR_GATE_RED'):
                v.verify(pilot, FIXTURE)

    def test_synthetic_verifier_wrong_claim_and_missing_row(self):
        with tempfile.TemporaryDirectory() as td:
            pilot = self.make_synthetic(td)
            path = pilot / 'raw/03_COPY_BASELINE.json'
            row = json.loads(path.read_text())
            row['final_output'] = row['final_output'].replace('Euro', 'Dollars')
            path.write_text(json.dumps(row))
            with self.assertRaisesRegex(ValueError, 'RUN13T_SCORE_OR_FIDELITY_RED'):
                v.verify(pilot, FIXTURE)
            path.unlink()
            with self.assertRaisesRegex(ValueError, 'RUN13T_RAW_COVERAGE_RED'):
                v.verify(pilot, FIXTURE)


if __name__ == '__main__':
    unittest.main()