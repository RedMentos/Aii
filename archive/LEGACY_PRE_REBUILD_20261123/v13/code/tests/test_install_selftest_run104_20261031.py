"""Run104 optional phone smoke: original registered cohorts remain immutable."""
import hashlib
import json
from pathlib import Path
import unittest

from scripts import install_selftest as smoke


HASHES = {
    'legacy_run97': '31b7d96ed740139b07b3b9dcf820aa04fafa13f5dfdcc4645e1df8e8df933f55',
    'run102_c3': '218303e408fab72d705dc3daa2f63dab63e0e34a7ab7ecc31f4954c585a563f5',
    'run104_c3_c5_exit': 'd745f4a1df7d54f7b1c1024e7d3aa24603d007070a694a6611d50ba958b96d70',
}
EXTRA = (
    'test_jef_c3_c5_c6_operator_cli.JefC3C5C6OperatorCliTests.test_six_source_bound_local_drafts_survive_restart',
    'test_jef_c3_c5_c6_operator_cli.JefC3C5C6OperatorCliTests.test_native_missing_pinned_model_refuses_before_human_records',
    'test_step2_exit_gate_split_20261031.Step2ExitGate.test_exit_is_explicitly_red_and_all_graph_deps_remain_known',
)


class Run104C3C5ExitSmokeCohort(unittest.TestCase):
    def test_original_cohorts_and_default_unchanged(self):
        self.assertEqual(set(smoke.COHORTS), set(HASHES))
        for name, digest in HASHES.items():
            cases = smoke.COHORTS[name]
            self.assertEqual(hashlib.sha256(json.dumps(
                cases, separators=(',', ':')).encode()).hexdigest(), digest)
            self.assertEqual(len(cases), 21 if name == 'run104_c3_c5_exit' else 18)
            self.assertEqual(len(set(cases)), len(cases))
        self.assertIs(smoke.COHORTS['legacy_run97'], smoke.SMOKE_CASES)
        self.assertIs(smoke.COHORTS['run102_c3'], smoke.SMOKE_CASES_RUN102_C3)
        self.assertEqual(smoke.run_bounded.__defaults__, (120, 'legacy_run97'))
        self.assertIn('scripts/install_selftest.py" --cohort run102_c3',
                      (Path(smoke.APP) / 'setup.sh').read_text())

    def test_three_crossorgan_checks_are_exact_appended_methods(self):
        names = smoke.SMOKE_CASES_RUN104_C3_C5_EXIT
        self.assertEqual(names[:18], smoke.SMOKE_CASES_RUN102_C3)
        self.assertEqual(names[18:], EXTRA)
        self.assertEqual(smoke.load_exact_suite(names).countTestCases(), 21)

    def test_actual_bounded_21_case_worker(self):
        self.assertEqual(smoke.run_bounded(120, 'run104_c3_c5_exit'), 0)

    def test_invalid_cohort_and_timeout_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'unknown install-smoke cohort'):
            smoke.run_bounded(5, 'run104_typo')
        for seconds in (0, 121, True, 0.5):
            with self.subTest(seconds=seconds):
                with self.assertRaises(ValueError):
                    smoke.run_bounded(seconds, 'run104_c3_c5_exit')


if __name__ == '__main__':
    unittest.main()
