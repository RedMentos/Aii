"""Persisted B3 L1 PASS labels require full canonical evidence on every read."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from v13 import b3bridge as BB

REQUIRED = ('beats_no_message', 'beats_latent_shuffled', 'beats_latent_random',
            'utility_beats_exact', 'utility_beats_control', 'utility_beats_symbolic',
            'role_retention', 'receiver_ood', 'restart_reproducibility')


def complete_gate():
    return {'verdict': 'PASS',
            'criteria': {name: {'significant': True} for name in REQUIRED},
            'missing_baselines': [], 'invalid_evidence': []}


class B3L1ReportRevalidationReview(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        (self.home / 'b3').mkdir()
        self.row = {'bridge': {'stale_receiver_revision': False},
                    'fallback_channel': 'SOURCE_EXACT', 'experience_count': 3,
                    'native_taps': True, 'receiver_tap_ids': ['synthetic'],
                    'latent_gain': .1, 'router_kl': .01,
                    'hardware_proof_id': 'synthetic_not_native_proof'}

    def write(self, gate):
        path = self.home / 'b3' / 'B1_TO_B2.json'
        path.write_text(json.dumps({
            'calibrated': True, 'receiver_revision': 'r1',
            'l1_gate': gate}))

    def assert_unavailable(self):
        doc = BB.doctor_fields(self.home, 'B1_TO_B2', 'r1')
        self.assertEqual(doc['latent_level'], 'unavailable')
        self.assertEqual(doc['latent_read_authority'], 0)
        g = BB.completion_gate(self.home, 'B1_TO_B2', self.row, messages=1)
        self.assertFalse(g['B3_LATENT_IMPLEMENTED'])
        self.assertNotIn(g['status'], ('L1_shadow', 'active'))
        self.assertEqual(g['latent_authority'], 0)

    def test_label_only_pass_cannot_become_l1_shadow_or_active(self):
        self.write({'verdict': 'PASS'})
        self.assert_unavailable()

    def test_each_missing_or_negative_criterion_revokes_report(self):
        for name in REQUIRED:
            with self.subTest(name=name, kind='missing'):
                gate = complete_gate()
                del gate['criteria'][name]
                self.write(gate)
                self.assert_unavailable()
            with self.subTest(name=name, kind='false'):
                gate = complete_gate()
                gate['criteria'][name]['significant'] = False
                self.write(gate)
                self.assert_unavailable()

    def test_missing_baselines_and_invalid_markers_revoke_pass(self):
        for field, value in (('missing_baselines', ['CONTROL']),
                             ('invalid_evidence', ['LATENT:invalid_accuracy']),
                             ('criteria', None)):
            with self.subTest(field=field):
                gate = complete_gate()
                gate[field] = value
                self.write(gate)
                self.assert_unavailable()

    def test_complete_synthetic_report_and_stale_revision_control(self):
        self.write(complete_gate())
        doc = BB.doctor_fields(self.home, 'B1_TO_B2', 'r1')
        self.assertEqual(doc['latent_level'], 'L1_PASSED_L2_SHADOW_ALLOWED')
        self.assertEqual(doc['latent_read_authority'], 0)
        g = BB.completion_gate(self.home, 'B1_TO_B2', self.row, messages=1)
        self.assertEqual(g['status'], 'active')  # synthetic report contract only
        self.assertEqual(g['latent_authority'], 0)
        self.row['bridge']['stale_receiver_revision'] = True
        self.assertFalse(BB.completion_gate(self.home, 'B1_TO_B2', self.row,
                                            messages=1)['B3_LATENT_IMPLEMENTED'])
        self.assertEqual(BB.doctor_fields(self.home, 'B1_TO_B2', 'r2')['latent_level'],
                         'unavailable')


if __name__ == '__main__':
    unittest.main()
