"""Run317 preregistered source-use diagnostic: fixture/software only.

Real native evidence comes exclusively from the separate pinned GitHub CI stage.
"""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import native_c3_source_use_ablation_run317 as R
from v13 import prompts
from v13.common import atomic_write, dumps


class Run317SourceUseAblation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name) / 'out'
        self.original = prompts.TEXT['en']['memories']

    def tearDown(self):
        self.assertEqual(prompts.TEXT['en']['memories'], self.original)
        self.tmp.cleanup()

    def mock_probe(self, home, models_from, raw, native, timeout):
        # This test double cannot be counted as native evidence.
        code = R.P.CODE
        question = R.P.QUESTION
        result = {
            'status': 'COMPLETE', 'native': False,
            'question': question, 'synthetic_correction': code,
            'stages': [{'stage': 'before'}, {'stage': 'after_correction'},
                       {'stage': 'after_forget'}],
            'integration_pass': True, 'utility_pass': True,
            'utility': {'second_exact': True, 'observed_improvement': True,
                        'forget_output_nonretention': True},
            'diagnostic_header_sha256': R.sha_text(prompts.TEXT['en']['memories']),
        }
        atomic_write(raw, (dumps(result) + '\n').encode())
        return result

    def test_frozen_cases_headers_and_counterbalanced_order(self):
        R.verify_registration()
        self.assertEqual(len(R.ORDER), 10)
        self.assertEqual(set(R.ORDER), {(x['id'], a) for x in R.C.CASES for a in ('A', 'B')})
        self.assertEqual(R.sha_text(R.BASELINE), R.HEADER_SHA['A'])
        self.assertEqual(R.sha_text(R.CANDIDATE), R.HEADER_SHA['B'])
        self.assertEqual(R.C.registry_sha(), R.C.COHORT_SHA256)

    def test_scoped_patch_restores_globals_even_on_exception(self):
        old_question, old_code = R.P.QUESTION, R.P.CODE
        with self.assertRaisesRegex(RuntimeError, 'forced'):
            with R.scoped_case(R.CASE_BY_ID['CEDAR'], 'B'):
                self.assertEqual(prompts.TEXT['en']['memories'], R.CANDIDATE)
                self.assertEqual(R.P.CODE, '27615')
                raise RuntimeError('forced')
        self.assertEqual(R.P.QUESTION, old_question)
        self.assertEqual(R.P.CODE, old_code)

    def test_full_fixture_all_ten_and_no_hidden_denominator(self):
        with patch.object(R.P, 'probe', side_effect=self.mock_probe) as fake:
            report = R.run(self.out, native=False)
        self.assertEqual(fake.call_count, 10)
        self.assertEqual(report['status'], 'COMPLETE')
        self.assertEqual(report['evidence_level'], 'FIXTURE_ONLY')
        self.assertEqual([report['metrics']['arms'][x]['attempted'] for x in ('A', 'B')], [5, 5])
        self.assertEqual(report['metrics']['paired_counts']['utility_delta_B_minus_A'], 0)
        self.assertEqual(len(report['cases']), 10)
        for row in report['cases']:
            raw = json.loads((self.out / ('RUN317_' + row['case_id'] + '_' + row['arm'] + '.json')).read_text())
            self.assertEqual(raw['diagnostic_header_sha256'], R.HEADER_SHA[row['arm']])

    def test_resume_does_not_rewrite_closed_raw_cases(self):
        with patch.object(R.P, 'probe', side_effect=self.mock_probe):
            R.run(self.out, native=False)
        original = (self.out / 'RUN317_CEDAR_A.json').read_bytes()
        with patch.object(R.P, 'probe', side_effect=AssertionError('unexpected rerun')):
            report = R.run(self.out, native=False)
        self.assertEqual(report['status'], 'COMPLETE')
        self.assertEqual((self.out / 'RUN317_CEDAR_A.json').read_bytes(), original)

    def test_tampered_raw_and_aggregate_are_rejected(self):
        with patch.object(R.P, 'probe', side_effect=self.mock_probe):
            R.run(self.out, native=False)
        raw = self.out / 'RUN317_CEDAR_B.json'
        before = raw.read_bytes()
        raw.write_bytes(before + b' ')
        with self.assertRaisesRegex(ValueError, 'raw bytes'):
            R.run(self.out, native=False)
        raw.write_bytes(before)
        aggregate = self.out / 'RUN317_ABLATION.json'
        report = json.loads(aggregate.read_text())
        report['cases'][0]['utility_pass'] = False
        aggregate.write_text(dumps(report))
        with self.assertRaisesRegex(ValueError, 'aggregate differs'):
            R.run(self.out, native=False)

    def test_resume_refuses_different_evidence_level_and_header(self):
        with patch.object(R.P, 'probe', side_effect=self.mock_probe):
            R.run(self.out, native=False)
        with self.assertRaisesRegex(ValueError, 'identity mismatch'):
            R.run(self.out, native=True)
        aggregate = self.out / 'RUN317_ABLATION.json'
        report = json.loads(aggregate.read_text())
        report['header_sha256']['B'] = '0' * 64
        aggregate.write_text(dumps(report))
        with self.assertRaisesRegex(ValueError, 'identity mismatch'):
            R.run(self.out, native=False)

    def test_negative_semantic_utility_is_counted_without_false_pass(self):
        def failing_cedar(home, models_from, raw, native, timeout):
            result = self.mock_probe(home, models_from, raw, native, timeout)
            if R.P.CODE == '27615' and prompts.TEXT['en']['memories'] == R.CANDIDATE:
                result['utility_pass'] = False
                result['utility']['second_exact'] = False
                result['utility']['observed_improvement'] = False
                atomic_write(raw, (dumps(result) + '\n').encode())
            return result
        with patch.object(R.P, 'probe', side_effect=failing_cedar):
            report = R.run(self.out, native=False)
        self.assertEqual(report['status'], 'COMPLETE')
        self.assertEqual(report['metrics']['arms']['A']['utility'], 5)
        self.assertEqual(report['metrics']['arms']['B']['utility'], 4)
        self.assertEqual(report['metrics']['paired_counts']['utility_delta_B_minus_A'], -1)

    def test_real_sqlite_runtime_fixture_only_all_30_turns(self):
        # No native model loaded; exercises actual Memory/Runtime/Store and scoped prompts.
        report = R.run(self.out, native=False, timeout=30)
        self.assertEqual(report['status'], 'COMPLETE')
        self.assertEqual(len(report['cases']), 10)
        self.assertTrue(all(x['native_stages'] == 3 for x in report['cases']))
        self.assertEqual(report['metrics']['arms']['A']['integration'], 5)
        self.assertEqual(report['metrics']['arms']['B']['integration'], 5)
        self.assertTrue(all(x['model_sha256'] is None for x in report['cases']))


if __name__ == '__main__':
    unittest.main()
