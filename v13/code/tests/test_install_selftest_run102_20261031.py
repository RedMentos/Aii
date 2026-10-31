"""Run102 first-install cohort: original frozen 18 cases remain byte-identical."""
import hashlib
import json
from pathlib import Path
import unittest
from scripts import install_selftest as smoke


def cohort_hash(names):
    return hashlib.sha256(json.dumps(names, separators=(',', ':')).encode()).hexdigest()


class Run102InstallSmokeCohort(unittest.TestCase):
    def test_original_legacy_run97_allowlist_is_unchanged(self):
        self.assertEqual(len(smoke.SMOKE_CASES), 18)
        self.assertEqual(cohort_hash(smoke.SMOKE_CASES),
                         '31b7d96ed740139b07b3b9dcf820aa04fafa13f5dfdcc4645e1df8e8df933f55')
        self.assertEqual(smoke.COHORTS['legacy_run97'], smoke.SMOKE_CASES)
        self.assertEqual(smoke.load_exact_suite().countTestCases(), 18)
        self.assertTrue(all(x.startswith('test_source_handoff_candidate.')
                            for x in smoke.SMOKE_CASES[12:17]))

    def test_new_cohort_is_fixed_exact_18_and_disjoint_at_five_methods(self):
        names = smoke.SMOKE_CASES_RUN102_C3
        self.assertEqual(len(names), 18)
        self.assertEqual(len(set(names)), 18)
        self.assertEqual(cohort_hash(names),
                         '218303e408fab72d705dc3daa2f63dab63e0e34a7ab7ecc31f4954c585a563f5')
        self.assertEqual(names[:12], smoke.SMOKE_CASES[:12])
        self.assertEqual(names[-1], smoke.SMOKE_CASES[-1])
        self.assertFalse(any(x.startswith('test_source_handoff_candidate.') for x in names))
        self.assertEqual(sum(x.startswith('test_b2_c3_context_plan_20261031.') for x in names), 3)
        self.assertEqual(sum(x.startswith('test_context_os.PlanTests.') for x in names), 2)
        self.assertEqual(smoke.load_exact_suite(names).countTestCases(), 18)

    def test_current_exact_cohort_passes_in_real_bounded_worker(self):
        self.assertEqual(smoke.run_bounded(120, 'run102_c3'), 0)

    def test_unknown_cohort_and_timeout_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'unknown install-smoke cohort'):
            smoke.run_bounded(10, 'missing')
        with self.assertRaises(ValueError):
            smoke.run_bounded(0, 'run102_c3')

    def test_setup_invokes_new_named_cohort_without_changing_legacy_default(self):
        setup = (Path(smoke.APP) / 'setup.sh').read_text()
        self.assertIn('scripts/install_selftest.py" --cohort run102_c3', setup)
        self.assertEqual(smoke.run_bounded.__defaults__, (120, 'legacy_run97'))


if __name__ == '__main__':
    unittest.main()
