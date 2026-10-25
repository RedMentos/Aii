"""Run201: reject invalid Age evidence before persistent maturity/stage mutation.

All raised-stage checks use temporary Store and test-only build_ceiling=5.
No native model, Redmi, learned quality, or real Age promotion claim.
"""
import math
import tempfile
import unittest
from pathlib import Path

from v13.age import AgeControl, gate_pass
from v13.config import initialize
from v13.store import Store


GOOD = {
    'experience': 60,
    'competence': .95,
    'stability': .95,
    'retention': .98,
    'calibration': .90,
    'memory_health': .97,
    'safe_self_control': .999,
    'regression_pass': True,
}


class AgeEvidenceFiniteRun201(unittest.TestCase):
    def check_rejected_without_state_change(self, metrics):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            cfg = initialize(home)
            cfg['user_stage_cap'] = 5
            store = Store(home)
            try:
                age = AgeControl(store, cfg, build_ceiling=5)  # TEST ONLY
                before = age.state()
                with self.assertRaises(ValueError):
                    age.record('system', metrics, evidence_id='bad-evidence')
                self.assertEqual(age.state(), before)
                self.assertEqual(age.system_stage(), 0)
                self.assertFalse(gate_pass(metrics, 1))
            finally:
                store.close()

    def test_nonfinite_or_nonnatural_experience_cannot_count_as_evidence(self):
        for invalid in (float('nan'), float('inf'), -float('inf'), True, -1, .5):
            with self.subTest(experience=repr(invalid)):
                self.check_rejected_without_state_change(dict(GOOD, experience=invalid))

    def test_nonfinite_boolean_and_out_of_range_quality_cannot_poison_maturity(self):
        for field, invalid in (
            ('competence', float('nan')),
            ('retention', float('inf')),
            ('stability', -.1),
            ('calibration', 1.2),
            ('memory_health', True),
            ('safe_self_control', True),
            ('regression_pass', 1),
        ):
            with self.subTest(field=field, invalid=repr(invalid)):
                self.check_rejected_without_state_change(dict(GOOD, **{field: invalid}))

    def test_missing_measurements_are_allowed_but_not_promoting(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            cfg = initialize(home)
            cfg['user_stage_cap'] = 5
            store = Store(home)
            try:
                age = AgeControl(store, cfg, build_ceiling=5)
                partial = dict(GOOD, experience=None, retention=None)
                self.assertFalse(gate_pass(partial, 1))
                out = age.record('system', partial, evidence_id='missing-measurement')
                self.assertEqual(out['stage'], 0)
                self.assertIsNone(out.get('proposal'))
            finally:
                store.close()

    def test_valid_age_evidence_keeps_original_three_distinct_records_gate(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            cfg = initialize(home)
            cfg['user_stage_cap'] = 5
            store = Store(home)
            try:
                age = AgeControl(store, cfg, build_ceiling=5)
                for i in range(2):
                    self.assertIsNone(age.record('system', GOOD, evidence_id=f'valid-{i}')['change'])
                self.assertEqual(age.system_stage(), 0)
                third = age.record('system', GOOD, evidence_id='valid-2')
                self.assertEqual(third['change']['kind'], 'PROMOTE')
                self.assertEqual(age.system_stage(), 1)
                self.assertTrue(gate_pass(GOOD, 1))
            finally:
                store.close()


if __name__ == '__main__':
    unittest.main()
