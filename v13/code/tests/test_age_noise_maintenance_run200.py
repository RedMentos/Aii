"""Run200: Age noise-aware competence tolerance cannot mask unrelated gate failures.

Software/synthetic evidence only. No Age>0 production authority: BUILD_CEILING=0.
The elevated test-only ceiling makes the existing maintenance branch observable.
"""
from pathlib import Path
import tempfile
import unittest

from v13.age import AgeControl
from v13.config import initialize
from v13.store import Store


GOOD = {
    'experience': 60,
    'competence': .95,
    'stability': .95,
    'retention': .98,
    'calibration': .9,
    'memory_health': .97,
    'safe_self_control': .999,
    'regression_pass': True,
}


class AgeNoiseMaintenanceRun200(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.cfg = initialize(self.home)
        self.cfg.update(user_stage_cap=5, age_plasticity_policy='noise_aware')
        self.store = Store(self.home)
        self.age = AgeControl(self.store, self.cfg, build_ceiling=5)  # TEST ONLY

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def prime(self):
        for i in range(5):
            self.age.record('system', GOOD, evidence_id=f'prime-{i}')
        self.assertEqual(self.age.system_stage(), 1)
        self.assertGreaterEqual(self.age.state()[0]['system']['noise']['n'], 4)

    def test_retention_regression_cannot_be_masked_by_rising_competence(self):
        self.prime()
        metrics = dict(GOOD, competence=.99, retention=.20)
        first = self.age.record('system', metrics, evidence_id='retention-first')
        self.assertNotEqual(first.get('noise'), 'FAIL_WITHIN_NOISE_BAND')
        self.assertEqual(self.age.state()[0]['system']['fail_streak'], 1)
        second = self.age.record('system', metrics, evidence_id='retention-second')
        self.assertEqual(second['change']['kind'], 'DEMOTE')
        self.assertEqual(self.age.system_stage(), 0)

    def test_all_other_maintenance_metrics_are_independent(self):
        for field, bad in (
            ('stability', .1),
            ('calibration', .1),
            ('memory_health', .1),
            ('safe_self_control', .1),
            ('experience', 0),
            ('regression_pass', False),
        ):
            with self.subTest(field=field):
                # Each case uses a fresh store so the second failure cannot
                # be attributed to a previous subcase.
                with tempfile.TemporaryDirectory() as td:
                    home = Path(td)
                    cfg = initialize(home)
                    cfg.update(user_stage_cap=5, age_plasticity_policy='noise_aware')
                    store = Store(home)
                    try:
                        a = AgeControl(store, cfg, build_ceiling=5)
                        for i in range(5):
                            a.record('system', GOOD, evidence_id=f'prime-{i}')
                        metrics = dict(GOOD, competence=.99, **{field: bad})
                        first = a.record('system', metrics, evidence_id='failure-1')
                        self.assertNotEqual(first.get('noise'), 'FAIL_WITHIN_NOISE_BAND')
                        self.assertEqual(a.state()[0]['system']['fail_streak'], 1)
                        second = a.record('system', metrics, evidence_id='failure-2')
                        self.assertEqual(second['change']['kind'], 'DEMOTE')
                    finally:
                        store.close()

    def test_competence_only_noise_still_suppresses_single_metric_failure(self):
        self.prime()
        metrics = dict(GOOD, competence=.2)
        first = self.age.record('system', metrics, evidence_id='competence-only')
        self.assertEqual(first.get('noise'), 'FAIL_WITHIN_NOISE_BAND')
        self.assertEqual(self.age.system_stage(), 1)
        self.assertEqual(self.age.state()[0]['system']['fail_streak'], 0)


if __name__ == '__main__':
    unittest.main()
